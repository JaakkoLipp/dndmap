import os
import types
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import mint_token
from app.core.config import Settings
from app.domain.models import utc_now
from app.main import create_app
from app.repositories.in_memory import InMemoryMapStore

AUTH_SETTINGS = Settings(
    app_name="Test D&D Map API",
    environment="test",
    api_prefix="/api/v1",
    enable_cors=False,
    auth_enabled=True,
    jwt_secret="test-jwt-secret-that-is-at-least-32-chars",
    jwt_algorithm="HS256",
    jwt_expire_minutes=60,
    session_secret="test-session-secret-at-least-32-chars",
)


@pytest.fixture()
def client() -> TestClient:
    settings = Settings(
        app_name="Test D&D Map API",
        environment="test",
        api_prefix="/api/v1",
        enable_cors=False,
    )
    app = create_app(settings=settings, store=InMemoryMapStore())
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def test_user():
    return types.SimpleNamespace(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        display_name="Test User",
        avatar_url=None,
        created_at=utc_now(),
        updated_at=utc_now(),
    )


@pytest.fixture()
def auth_token(test_user) -> str:
    return mint_token(test_user.id, AUTH_SETTINGS)


@pytest.fixture()
def mock_db() -> AsyncMock:
    db = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    db.get = AsyncMock(return_value=None)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture()
def auth_client(test_user, mock_db) -> TestClient:
    from app.auth.dependencies import get_current_user, get_optional_current_user
    from app.db.session import get_db, get_optional_db

    app = create_app(settings=AUTH_SETTINGS, store=InMemoryMapStore())

    async def _user():
        return test_user

    async def _db():
        yield mock_db

    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_optional_current_user] = _user
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_optional_db] = _db

    with TestClient(app) as tc:
        yield tc


@pytest.fixture(scope="session")
def postgres_url() -> str | None:
    """Skip postgres integration tests when POSTGRES_TEST_URL is not set."""
    url = os.environ.get("POSTGRES_TEST_URL")
    if not url:
        pytest.skip("POSTGRES_TEST_URL not set — skipping postgres integration tests")
    return url
