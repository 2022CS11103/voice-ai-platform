from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

connect_args = {}
if settings.is_sqlite:
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    # Import models so metadata is registered
    from app.db import models  # noqa: F401

    if settings.use_pgvector:
        from sqlalchemy import text

        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Lightweight SQLite column adds for evolving MVP schema
    if settings.is_sqlite:
        from sqlalchemy import text

        alters = [
            "ALTER TABLE appointments ADD COLUMN party_size INTEGER DEFAULT 1",
            "ALTER TABLE appointments ADD COLUMN email VARCHAR(255)",
            "ALTER TABLE appointments ADD COLUMN source VARCHAR(50) DEFAULT 'voice'",
            "ALTER TABLE users ADD COLUMN phone VARCHAR(30)",
        ]
        async with engine.begin() as conn:
            for stmt in alters:
                try:
                    await conn.execute(text(stmt))
                except Exception:
                    pass  # column already exists
            try:
                await conn.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone_unique "
                        "ON users(phone) WHERE phone IS NOT NULL"
                    )
                )
            except Exception:
                try:
                    await conn.execute(
                        text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone ON users(phone)")
                    )
                except Exception:
                    pass

