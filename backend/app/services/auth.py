from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import User
from app.db.session import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)
settings = get_settings()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload.get("sub", 0))
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
