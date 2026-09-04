from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Business, User
from app.db.session import get_db
from app.schemas import LoginRequest, SignupRequest, TokenResponse, UserOut
from app.services.auth import create_access_token, get_current_user, hash_password, verify_password
from app.services.validators import normalize_email, normalize_phone, validate_business_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)):
    try:
        email = validate_business_email(str(payload.email))
        phone = normalize_phone(payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing_email = await db.execute(select(User).where(User.email == email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="This email is already registered. Please sign in instead.",
        )

    existing_phone = await db.execute(select(User).where(User.phone == phone))
    if existing_phone.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="This phone number is already registered with another account.",
        )

    user = User(
        email=email,
        phone=phone,
        name=payload.name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()
    db.add(
        Business(
            user_id=user.id,
            name=f"{payload.name}'s Business",
            industry="general",
            phone=phone,
        )
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Email or phone already registered.",
        ) from exc

    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        email = normalize_email(str(payload.email))
        # Soft-validate format on login too
        validate_business_email(email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return TokenResponse(access_token=create_access_token(user.id, user.email))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
