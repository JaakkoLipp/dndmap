"""Tests for the in-memory rate limiter and its HTTP enforcement."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.rate_limit import RateLimiter
from app.main import create_app
from app.repositories.in_memory import InMemoryMapStore


async def test_in_memory_limiter_blocks_after_limit() -> None:
    limiter = RateLimiter()
    for _ in range(3):
        assert await limiter.hit("k", limit=3, window_seconds=60) is True
    assert await limiter.hit("k", limit=3, window_seconds=60) is False


async def test_in_memory_limiter_resets_after_window() -> None:
    limiter = RateLimiter()
    assert await limiter.hit("k", limit=1, window_seconds=0) is True
    # window=0 means each call is a fresh window
    assert await limiter.hit("k", limit=1, window_seconds=0) is True


def test_upload_endpoint_returns_429_when_rate_limit_enabled() -> None:
    settings = Settings(
        app_name="Test",
        environment="test",
        api_prefix="/api/v1",
        enable_cors=False,
        rate_limit_enabled=True,
    )
    app = create_app(settings=settings, store=InMemoryMapStore())
    with TestClient(app) as client:
        # Create a map first so the upload route can find it.
        campaign = client.post("/api/v1/campaigns", json={"name": "RL"}).json()
        campaign_map = client.post(
            f"/api/v1/campaigns/{campaign['id']}/maps",
            json={"name": "M", "width": 10, "height": 10},
        ).json()

        # The upload limit is 10/min. After 10 successful or failed uploads
        # the 11th must return 429.
        for _ in range(10):
            response = client.post(
                f"/api/v1/maps/{campaign_map['id']}/image",
                files={"file": ("x.txt", b"not an image", "text/plain")},
            )
            # Will be 415 (not image) but the limiter still counts the call.
            assert response.status_code in (415, 429)

        response = client.post(
            f"/api/v1/maps/{campaign_map['id']}/image",
            files={"file": ("x.txt", b"not an image", "text/plain")},
        )
        assert response.status_code == 429
