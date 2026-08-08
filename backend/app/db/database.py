from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.config import settings

# Synchronous database setup
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.debug
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Async database setup
async_engine = create_async_engine(
    settings.database_async_url,
    echo=settings.debug,
    future=True
)

AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def init_db():
    """Dev-only convenience: create tables directly, bypassing Alembic.

    Real schema provisioning is `alembic upgrade head`. Kept for tests
    (which use their own throwaway SQLite engine) and quick local checks —
    not called automatically on app startup.
    """
    Base.metadata.create_all(bind=engine)
