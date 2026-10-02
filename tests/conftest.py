from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.core.database import Base, async_session_null_pool, engine_null_pool
from app.domains.dependencies import get_db
from app.main import app
from app.uow import UnitOfWork

settings = get_settings()


@pytest.fixture(autouse=True, scope="session")
def check_test_mode():
    assert settings.ENVIRONMENT == "TEST"


async def get_db_null_pool():
    async with UnitOfWork(session_factory=async_session_null_pool) as db:
        yield db


app.dependency_overrides[get_db] = get_db_null_pool


@pytest.fixture
async def db():
    async for db in get_db_null_pool():
        yield db


@pytest.fixture(autouse=True)
async def setup_database(check_test_mode):
    async with engine_null_pool.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(scope="session")
async def async_client() -> AsyncGenerator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
