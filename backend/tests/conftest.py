import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://realty:realty@localhost:5432/realty_test"
)

from src.db import Base, get_db  # noqa: E402
from src.main import app  # noqa: E402

TEST_DATABASE_URL = os.environ["DATABASE_URL"]


def _make_engine():
    return create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)


# --- Schema lifecycle (synchronous so it never touches the test event loop) ---

@pytest.fixture(scope="session")
def create_tables():
    """Create schema once before DB tests; drop after. Runs sync via asyncio.run()."""

    async def _up():
        engine = _make_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    async def _down():
        engine = _make_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(_up())
    yield
    asyncio.run(_down())


# --- Per-test DB session (each test gets its own connection via NullPool) ---

@pytest_asyncio.fixture
async def db_session(create_tables):  # noqa: F811  # triggers create_tables for DB tests
    engine = _make_engine()
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
