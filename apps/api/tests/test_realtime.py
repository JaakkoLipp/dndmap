"""Tests for the realtime WebSocket route and broker fanout."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import Settings
from app.main import create_app
from app.realtime.events import EventType
from app.repositories.in_memory import InMemoryMapStore


def create_campaign(client: TestClient) -> dict:
    response = client.post("/api/v1/campaigns", json={"name": "Northreach"})
    assert response.status_code == 201
    return response.json()


def create_map(client: TestClient, campaign_id: str) -> dict:
    response = client.post(
        f"/api/v1/campaigns/{campaign_id}/maps",
        json={"name": "Gloamwood", "width": 2400, "height": 1800},
    )
    assert response.status_code == 201
    return response.json()


def drain_until(ws, predicate, *, max_messages: int = 8) -> dict:
    for _ in range(max_messages):
        event = ws.receive_json()
        if predicate(event):
            return event
    raise AssertionError(f"Did not receive a matching event in {max_messages} reads")


def test_websocket_sends_connect_and_presence_snapshot(client: TestClient) -> None:
    campaign = create_campaign(client)
    campaign_map = create_map(client, campaign["id"])

    with client.websocket_connect(
        f"/api/v1/ws/campaigns/{campaign['id']}/maps/{campaign_map['id']}"
    ) as ws:
        connected = ws.receive_json()
        snapshot = ws.receive_json()

    assert connected["type"] == EventType.MAP_CONNECTED
    assert connected["map_id"] == campaign_map["id"]
    assert "client_id" in connected["payload"]

    assert snapshot["type"] == EventType.PRESENCE_SNAPSHOT
    assert snapshot["map_id"] == campaign_map["id"]
    assert len(snapshot["payload"]["actors"]) == 1


def test_websocket_relays_client_messages_to_other_sockets(client: TestClient) -> None:
    campaign = create_campaign(client)
    campaign_map = create_map(client, campaign["id"])

    url = f"/api/v1/ws/campaigns/{campaign['id']}/maps/{campaign_map['id']}"
    with client.websocket_connect(url) as ws_a, client.websocket_connect(url) as ws_b:
        ws_a.receive_json()  # map.connected
        ws_a.receive_json()  # presence.snapshot
        drain_until(ws_a, lambda e: e["type"] == EventType.PRESENCE_JOINED)

        ws_b.receive_json()  # map.connected
        ws_b.receive_json()  # presence.snapshot

        ws_a.send_json({"type": "object.moved", "object_id": "marker-1", "x": 5})

        event = drain_until(ws_b, lambda e: e["type"] == "object.moved")
        assert event["map_id"] == campaign_map["id"]
        assert event["payload"]["object_id"] == "marker-1"


def test_websocket_rejects_unknown_map(client: TestClient) -> None:
    campaign = create_campaign(client)
    bogus_map = uuid.uuid4()
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/api/v1/ws/campaigns/{campaign['id']}/maps/{bogus_map}"
        ) as ws:
            ws.receive_json()


def test_websocket_requires_auth_cookie_when_auth_enabled() -> None:
    settings = Settings(
        app_name="Test",
        environment="test",
        api_prefix="/api/v1",
        enable_cors=False,
        auth_enabled=True,
        jwt_secret="test-jwt-secret-that-is-at-least-32-chars",
        session_secret="test-session-secret-at-least-32-chars",
    )
    store = InMemoryMapStore()
    app = create_app(settings=settings, store=store)

    import asyncio

    async def seed() -> tuple[str, str]:
        campaign = await store.create_campaign(name="Seed")
        campaign_map = await store.create_map(
            campaign_id=campaign.id,
            name="Test",
            width=100,
            height=100,
            grid_size=70,
        )
        return str(campaign.id), str(campaign_map.id)

    campaign_id, map_id = asyncio.get_event_loop().run_until_complete(seed())

    with TestClient(app) as tc:
        with pytest.raises(WebSocketDisconnect):
            with tc.websocket_connect(
                f"/api/v1/ws/campaigns/{campaign_id}/maps/{map_id}"
            ) as ws:
                ws.receive_json()


def test_rest_map_update_publishes_realtime_event(client: TestClient) -> None:
    campaign = create_campaign(client)
    campaign_map = create_map(client, campaign["id"])

    url = f"/api/v1/ws/campaigns/{campaign['id']}/maps/{campaign_map['id']}"
    with client.websocket_connect(url) as ws:
        ws.receive_json()  # map.connected
        ws.receive_json()  # presence.snapshot

        response = client.patch(
            f"/api/v1/maps/{campaign_map['id']}", json={"name": "Renamed"}
        )
        assert response.status_code == 200

        event = drain_until(ws, lambda e: e["type"] == EventType.MAP_UPDATED)
        assert event["map_id"] == campaign_map["id"]
        assert "name" in event["payload"]["fields"]


def test_rest_object_lifecycle_publishes_realtime_events(client: TestClient) -> None:
    campaign = create_campaign(client)
    campaign_map = create_map(client, campaign["id"])

    layer_resp = client.post(
        f"/api/v1/maps/{campaign_map['id']}/layers",
        json={"name": "Annotations", "kind": "notes"},
    )
    assert layer_resp.status_code == 201
    layer = layer_resp.json()

    url = f"/api/v1/ws/campaigns/{campaign['id']}/maps/{campaign_map['id']}"
    with client.websocket_connect(url) as ws:
        ws.receive_json()  # map.connected
        ws.receive_json()  # presence.snapshot

        create_resp = client.post(
            f"/api/v1/maps/{campaign_map['id']}/objects",
            json={
                "layer_id": layer["id"],
                "name": "Tower",
                "kind": "marker",
                "x": 1.0,
                "y": 2.0,
            },
        )
        assert create_resp.status_code == 201
        obj = create_resp.json()

        created_evt = drain_until(ws, lambda e: e["type"] == EventType.OBJECT_CREATED)
        assert created_evt["payload"]["object_id"] == obj["id"]

        update_resp = client.patch(
            f"/api/v1/objects/{obj['id']}", json={"x": 10.0, "y": 20.0}
        )
        assert update_resp.status_code == 200
        updated_evt = drain_until(ws, lambda e: e["type"] == EventType.OBJECT_UPDATED)
        assert updated_evt["payload"]["object_id"] == obj["id"]

        delete_resp = client.delete(f"/api/v1/objects/{obj['id']}")
        assert delete_resp.status_code == 204
        deleted_evt = drain_until(ws, lambda e: e["type"] == EventType.OBJECT_DELETED)
        assert deleted_evt["payload"]["object_id"] == obj["id"]
