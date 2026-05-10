"""Tests for the map revision history endpoint.

Revision writes require a Postgres session, so in-memory mode returns an
empty list. Verifying that contract is enough at this layer — the
Postgres-integration suite covers the actual write path when configured.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_map(client: TestClient):
    campaign = client.post("/api/v1/campaigns", json={"name": "Audit"}).json()
    campaign_map = client.post(
        f"/api/v1/campaigns/{campaign['id']}/maps",
        json={"name": "M", "width": 100, "height": 100},
    ).json()
    return campaign, campaign_map


def test_list_revisions_returns_empty_in_memory_mode(client: TestClient) -> None:
    _, campaign_map = _create_map(client)
    response = client.get(f"/api/v1/maps/{campaign_map['id']}/revisions")
    assert response.status_code == 200
    assert response.json() == []


def test_list_revisions_404_for_unknown_map(client: TestClient) -> None:
    import uuid

    response = client.get(f"/api/v1/maps/{uuid.uuid4()}/revisions")
    assert response.status_code == 404


def test_list_revisions_respects_limit_param(client: TestClient) -> None:
    _, campaign_map = _create_map(client)
    response = client.get(
        f"/api/v1/maps/{campaign_map['id']}/revisions?limit=10"
    )
    assert response.status_code == 200
    too_large = client.get(
        f"/api/v1/maps/{campaign_map['id']}/revisions?limit=999"
    )
    assert too_large.status_code == 422
