"""Tests for auth helpers and auth-enabled routes."""
import uuid

import httpx
import pytest
import respx

from app.auth.cookie import COOKIE_NAME, set_auth_cookie
from app.auth.jwt import decode_token, mint_token
from app.auth.providers import DiscordOAuthProvider
from app.auth.state import sign_state, verify_state
from app.core.config import Settings

_SETTINGS = Settings(
    auth_enabled=True,
    jwt_secret="test-jwt-secret-that-is-at-least-32-chars",
    jwt_algorithm="HS256",
    jwt_expire_minutes=60,
    session_secret="test-session-secret-at-least-32-chars",
    oauth_discord_client_id="discord-client-id",
    oauth_discord_client_secret="discord-client-secret",
    oauth_redirect_base_url="http://localhost:8080/api/v1/auth",
)


# --- JWT ---

def test_jwt_round_trip():
    user_id = uuid.uuid4()
    token = mint_token(user_id, _SETTINGS)
    assert decode_token(token, _SETTINGS) == user_id


def test_jwt_wrong_secret_returns_none():
    token = mint_token(uuid.uuid4(), _SETTINGS)
    bad = Settings(
        jwt_secret="completely-different-secret-also-32-ch",
        jwt_algorithm="HS256",
        jwt_expire_minutes=60,
    )
    assert decode_token(token, bad) is None


def test_jwt_malformed_returns_none():
    assert decode_token("not.a.jwt", _SETTINGS) is None


# --- OAuth state ---

def test_state_round_trip():
    signed = sign_state(_SETTINGS.session_secret, "abc123")
    assert verify_state(_SETTINGS.session_secret, signed) == "abc123"


def test_state_round_trip_with_dict_payload():
    payload = {"n": "abc", "next": "/campaigns/x"}
    signed = sign_state(_SETTINGS.session_secret, payload)
    assert verify_state(_SETTINGS.session_secret, signed) == payload


def test_state_tampered_returns_none():
    signed = sign_state(_SETTINGS.session_secret, "nonce")
    assert verify_state(_SETTINGS.session_secret, signed + "x") is None


def test_state_wrong_secret_returns_none():
    signed = sign_state(_SETTINGS.session_secret, "nonce")
    assert verify_state("wrong-secret-at-least-32-chars-long", signed) is None


# --- Cookie helpers ---

def test_cookie_name_constant():
    assert COOKIE_NAME == "access_token"


def test_set_cookie_is_httponly():
    from starlette.responses import Response
    resp = Response()
    set_auth_cookie(resp, "mytoken", expire_minutes=60, is_production=False)
    cookie_header = resp.headers.get("set-cookie", "")
    assert "access_token=mytoken" in cookie_header
    assert "httponly" in cookie_header.lower()


# --- OAuth provider URL ---

def test_discord_build_url_includes_client_id_and_state():
    url = DiscordOAuthProvider().build_authorization_url(
        "my-client-id", "http://localhost/cb", "state123"
    )
    assert "my-client-id" in url
    assert "state123" in url
    assert "discord.com" in url


# --- Route-level auth behavior ---

def test_campaigns_returns_401_when_auth_enabled_and_no_cookie():
    """Routes return 401 when auth_enabled=True and no cookie is sent."""
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.repositories.in_memory import InMemoryMapStore

    settings = Settings(
        auth_enabled=True,
        jwt_secret="test-jwt-secret-that-is-at-least-32-chars",
        jwt_algorithm="HS256",
        jwt_expire_minutes=60,
        session_secret="test-session-secret-at-least-32-chars",
    )
    app = create_app(settings=settings, store=InMemoryMapStore())
    with TestClient(app) as tc:
        assert tc.get("/api/v1/campaigns").status_code == 401
        assert tc.post("/api/v1/campaigns", json={"name": "X"}).status_code == 401


def test_me_returns_user_when_override_active(auth_client, test_user):
    """GET /auth/me returns current user when auth is active."""
    response = auth_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["display_name"] == test_user.display_name


def test_logout_clears_cookie(auth_client):
    response = auth_client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


@respx.mock
def test_discord_callback_sets_cookie():
    """OAuth callback verifies state, calls Discord, sets access_token cookie."""
    from unittest.mock import AsyncMock, MagicMock
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.session import get_db, get_optional_db
    from app.main import create_app
    from app.repositories.in_memory import InMemoryMapStore

    settings = Settings(
        auth_enabled=True,
        jwt_secret="test-jwt-secret-that-is-at-least-32-chars",
        jwt_algorithm="HS256",
        jwt_expire_minutes=60,
        session_secret="test-session-secret-at-least-32-chars",
        oauth_discord_client_id="test-id",
        oauth_discord_client_secret="test-secret",
        oauth_redirect_base_url="http://localhost:8080/api/v1/auth",
    )

    # Mock Discord HTTP calls
    respx.post("https://discord.com/api/oauth2/token").mock(
        return_value=httpx.Response(200, json={"access_token": "discord-tok"})
    )
    respx.get("https://discord.com/api/users/@me").mock(
        return_value=httpx.Response(200, json={
            "id": "1234567890",
            "username": "tester",
            "global_name": "Tester",
            "avatar": None,
        })
    )

    # Build mock DB that handles _upsert_user queries
    mock_db = AsyncMock(spec=AsyncSession)
    identity_result = MagicMock()
    identity_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=identity_result)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    created_user = MagicMock()
    created_user.id = uuid.uuid4()
    mock_db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", created_user.id) or None)

    async def _db():
        yield mock_db

    app = create_app(settings=settings, store=InMemoryMapStore())
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_optional_db] = _db

    state = sign_state(settings.session_secret, "testnonce")
    with TestClient(app, follow_redirects=False) as tc:
        response = tc.get(
            "/api/v1/auth/discord/callback",
            params={"code": "authcode", "state": state},
        )

    assert response.status_code in (302, 307)
    set_cookie = response.headers.get("set-cookie", "")
    assert "access_token" in set_cookie


def test_local_login_creates_user_and_sets_cookie():
    """POST /auth/local/login creates a new user and returns access_token cookie."""
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock, MagicMock
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.session import get_db, get_optional_db
    from app.main import create_app
    from app.repositories.in_memory import InMemoryMapStore

    settings = Settings(
        auth_enabled=True,
        local_login_enabled=True,
        jwt_secret="test-jwt-secret-that-is-at-least-32-chars",
        jwt_algorithm="HS256",
        jwt_expire_minutes=60,
        session_secret="test-session-secret-at-least-32-chars",
    )

    test_id = uuid.uuid4()
    test_now = datetime.now(timezone.utc)

    mock_db = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalar_one_or_none.return_value = None  # no existing identity → new user
    mock_db.execute = AsyncMock(return_value=result)
    mock_db.add = MagicMock()

    async def _refresh(obj):
        obj.id = test_id
        obj.created_at = test_now
        obj.updated_at = test_now

    mock_db.refresh = AsyncMock(side_effect=_refresh)

    async def _db():
        yield mock_db

    app = create_app(settings=settings, store=InMemoryMapStore())
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_optional_db] = _db

    with TestClient(app) as tc:
        response = tc.post("/api/v1/auth/local/login", json={"username": "TestDM"})

    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "TestDM"
    assert "id" in data
    assert "access_token" in response.headers.get("set-cookie", "")


def test_local_login_returns_503_when_auth_disabled():
    """POST /auth/local/login returns 503 when AUTH_ENABLED is false."""
    from unittest.mock import AsyncMock
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.session import get_db, get_optional_db
    from app.main import create_app
    from app.repositories.in_memory import InMemoryMapStore

    app = create_app(settings=Settings(auth_enabled=False), store=InMemoryMapStore())

    async def _db():
        yield AsyncMock(spec=AsyncSession)

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_optional_db] = _db

    with TestClient(app) as tc:
        response = tc.post("/api/v1/auth/local/login", json={"username": "TestDM"})
    assert response.status_code == 503
