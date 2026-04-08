from collections.abc import AsyncGenerator

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.customer import Base

# Use TEST_DATABASE_URL env var if set, otherwise derive from DATABASE_URL
# Replace Docker hostname with localhost so tests work outside containers
_base, _db_name = settings.DATABASE_URL.rsplit("/", 1)
_default_test_url = f"{_base}/{_db_name}_test".replace("@postgres:", "@localhost:")
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", _default_test_url)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=True, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for each test.

    Creates all tables before the test and drops them after.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = TestSessionLocal()
    try:
        yield session
    finally:
        await session.close()
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client wired to the test database."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
