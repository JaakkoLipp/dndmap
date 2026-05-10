"""Tests for the campaign members management endpoints."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def test_list_members_returns_empty_in_dev_mode(client: TestClient) -> None:
    """Without auth, the route returns [] so the UI can render cleanly."""
    campaign = client.post("/api/v1/campaigns", json={"name": "Roster"}).json()
    response = client.get(f"/api/v1/campaigns/{campaign['id']}/members")
    assert response.status_code == 200
    assert response.json() == []


def test_change_role_requires_auth(client: TestClient) -> None:
    campaign = client.post("/api/v1/campaigns", json={"name": "Roster"}).json()
    response = client.patch(
        f"/api/v1/campaigns/{campaign['id']}/members/{uuid.uuid4()}",
        json={"role": "dm"},
    )
    assert response.status_code == 503


def test_remove_member_requires_auth(client: TestClient) -> None:
    campaign = client.post("/api/v1/campaigns", json={"name": "Roster"}).json()
    response = client.delete(
        f"/api/v1/campaigns/{campaign['id']}/members/{uuid.uuid4()}"
    )
    assert response.status_code == 503
