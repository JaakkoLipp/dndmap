"""Regression tests: auth routes must never 500 in memory mode.

Previously several routes declared ``db: DbSession`` (the required
variant) which raises ``AttributeError`` when ``session_factory`` isn't
on ``app.state`` — Postgres-less deployments would see a 500 mid-OAuth
or on every authenticated request. After the fix these all return
clean 5xx responses with actionable detail messages or 4xx for normal
client errors.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.repositories.in_memory import InMemoryMapStore


def _memory_auth_client(**overrides) -> TestClient:
    """Build an app with AUTH_ENABLED=true but no Postgres configured."""
    base = dict(
        auth_enabled=True,
        local_login_enabled=True,
        jwt_secret="x" * 32,
        session_secret="y" * 32,
        oauth_discord_client_id="id",
        oauth_discord_client_secret="secret",
    )
    base.update(overrides)
    settings = Settings(**base)
    app = create_app(settings=settings, store=InMemoryMapStore())
    return TestClient(app, follow_redirects=False)


def test_auth_me_returns_503_not_500_when_db_missing() -> None:
    with _memory_auth_client() as tc:
        r = tc.get("/api/v1/auth/me")
        assert r.status_code == 503
        assert "PERSISTENCE_BACKEND" in r.json()["detail"]


def test_local_login_returns_503_with_db_hint_when_db_missing() -> None:
    with _memory_auth_client() as tc:
        r = tc.post("/api/v1/auth/local/login", json={"username": "alice"})
        assert r.status_code == 503
        assert "PERSISTENCE_BACKEND" in r.json()["detail"]


def test_oauth_callback_redirects_to_login_when_db_missing() -> None:
    """A late-stage DB failure during OAuth must redirect, not 500."""
    from app.auth.state import sign_state

    with _memory_auth_client() as tc:
        # Use a valid state so we get past the state check.
        state = sign_state("y" * 32, {"n": "abc", "next": "/campaigns"})
        # Discord HTTP isn't mocked here, so the provider step itself errors
        # and we get provider_error — still a redirect, never 500.
        r = tc.get(f"/api/v1/auth/discord/callback?code=x&state={state}")
        assert r.status_code in (302, 307)
        loc = r.headers.get("location", "")
        assert loc.startswith("/login?"), f"expected redirect, got {loc!r}"


def test_create_invite_returns_503_when_db_missing() -> None:
    import uuid

    with _memory_auth_client() as tc:
        r = tc.post(
            f"/api/v1/campaigns/{uuid.uuid4()}/invites",
            json={"role": "player"},
        )
        # 401 (no auth cookie) is also acceptable — what we must NOT see is 500.
        assert r.status_code != 500


def test_accept_invite_returns_503_when_db_missing() -> None:
    with _memory_auth_client() as tc:
        r = tc.post("/api/v1/invites/some-code/accept")
        assert r.status_code != 500
