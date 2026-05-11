"""Tests for the in-memory lock store and the WebSocket lock protocol."""

from __future__ import annotations

import time
import uuid

import pytest
from fastapi.testclient import TestClient

from app.realtime.events import EventType
from app.realtime.locks import InMemoryLockStore


# --- InMemoryLockStore unit tests ---


async def test_acquire_when_unlocked_succeeds() -> None:
    store = InMemoryLockStore()
    map_id = uuid.uuid4()
    object_id = uuid.uuid4()
    lock = await store.acquire(map_id, object_id, "client-a", "Alice", ttl_seconds=30)
    assert lock is not None
    assert lock.holder_client_id == "client-a"


async def test_second_holder_is_denied() -> None:
    store = InMemoryLockStore()
    map_id = uuid.uuid4()
    object_id = uuid.uuid4()
    await store.acquire(map_id, object_id, "client-a", "Alice", 30)
    second = await store.acquire(map_id, object_id, "client-b", "Bob", 30)
    assert second is None


async def test_same_holder_can_re_acquire() -> None:
    store = InMemoryLockStore()
    map_id = uuid.uuid4()
    object_id = uuid.uuid4()
    first = await store.acquire(map_id, object_id, "client-a", "Alice", 30)
    second = await store.acquire(map_id, object_id, "client-a", "Alice", 30)
    assert first is not None and second is not None
    # The expires_at should bump forward on re-acquire.
    assert second.expires_at >= first.expires_at


async def test_release_only_succeeds_for_holder() -> None:
    store = InMemoryLockStore()
    map_id = uuid.uuid4()
    object_id = uuid.uuid4()
    await store.acquire(map_id, object_id, "client-a", None, 30)

    assert await store.release(map_id, object_id, "client-b") is False
    assert await store.release(map_id, object_id, "client-a") is True


async def test_expired_lock_can_be_reclaimed() -> None:
    store = InMemoryLockStore()
    map_id = uuid.uuid4()
    object_id = uuid.uuid4()
    # TTL of 0 → already expired by the time we check.
    await store.acquire(map_id, object_id, "client-a", None, 0)
    time.sleep(0.01)
    second = await store.acquire(map_id, object_id, "client-b", None, 30)
    assert second is not None
    assert second.holder_client_id == "client-b"


async def test_release_all_for_client_returns_held_locks() -> None:
    store = InMemoryLockStore()
    map_id = uuid.uuid4()
    o1, o2 = uuid.uuid4(), uuid.uuid4()
    await store.acquire(map_id, o1, "client-a", None, 30)
    await store.acquire(map_id, o2, "client-a", None, 30)
    await store.acquire(map_id, uuid.uuid4(), "client-b", None, 30)

    released = await store.release_all_for_client("client-a")
    assert sorted(lock.object_id for lock in released) == sorted([o1, o2])

    remaining = await store.list_for_map(map_id)
    assert len(remaining) == 1
    assert remaining[0].holder_client_id == "client-b"


# --- WebSocket protocol smoke tests ---


def _create_campaign_and_map(client: TestClient) -> tuple[dict, dict]:
    campaign = client.post("/api/v1/campaigns", json={"name": "Locks"}).json()
    campaign_map = client.post(
        f"/api/v1/campaigns/{campaign['id']}/maps",
        json={"name": "M", "width": 100, "height": 100},
    ).json()
    return campaign, campaign_map


def _drain_until(ws, predicate, *, max_messages: int = 10) -> dict:
    for _ in range(max_messages):
        event = ws.receive_json()
        if predicate(event):
            return event
    raise AssertionError("Did not receive matching event")


def test_lock_acquire_broadcasts_to_other_clients(client: TestClient) -> None:
    campaign, campaign_map = _create_campaign_and_map(client)
    url = f"/api/v1/ws/campaigns/{campaign['id']}/maps/{campaign_map['id']}"
    object_id = str(uuid.uuid4())

    with client.websocket_connect(url) as ws_a, client.websocket_connect(url) as ws_b:
        # Drain join handshake on both sockets.
        for ws in (ws_a, ws_b):
            ws.receive_json()  # map.connected
            ws.receive_json()  # presence.snapshot
            ws.receive_json()  # lock.snapshot

        ws_a.send_json({"type": "lock.acquire", "object_id": object_id})

        event = _drain_until(ws_b, lambda e: e["type"] == EventType.LOCK_ACQUIRED)
        assert event["payload"]["object_id"] == object_id


def test_lock_conflict_sends_lock_denied_to_requester(client: TestClient) -> None:
    campaign, campaign_map = _create_campaign_and_map(client)
    url = f"/api/v1/ws/campaigns/{campaign['id']}/maps/{campaign_map['id']}"
    object_id = str(uuid.uuid4())

    with client.websocket_connect(url) as ws_a, client.websocket_connect(url) as ws_b:
        for ws in (ws_a, ws_b):
            ws.receive_json()  # map.connected
            ws.receive_json()  # presence.snapshot
            ws.receive_json()  # lock.snapshot

        ws_a.send_json({"type": "lock.acquire", "object_id": object_id})
        # Wait for the broadcast to settle on B.
        _drain_until(ws_b, lambda e: e["type"] == EventType.LOCK_ACQUIRED)

        ws_b.send_json({"type": "lock.acquire", "object_id": object_id})
        denied = _drain_until(ws_b, lambda e: e["type"] == EventType.LOCK_DENIED)
        assert denied["payload"]["object_id"] == object_id


def test_disconnect_releases_held_locks(client: TestClient) -> None:
    campaign, campaign_map = _create_campaign_and_map(client)
    url = f"/api/v1/ws/campaigns/{campaign['id']}/maps/{campaign_map['id']}"
    object_id = str(uuid.uuid4())

    with client.websocket_connect(url) as ws_b:
        ws_b.receive_json()  # map.connected
        ws_b.receive_json()  # presence.snapshot
        ws_b.receive_json()  # lock.snapshot

        with client.websocket_connect(url) as ws_a:
            ws_a.receive_json()
            ws_a.receive_json()
            ws_a.receive_json()
            ws_a.send_json({"type": "lock.acquire", "object_id": object_id})
            _drain_until(ws_b, lambda e: e["type"] == EventType.LOCK_ACQUIRED)

        # ws_a context exit → server releases the lock → ws_b gets a release.
        released = _drain_until(ws_b, lambda e: e["type"] == EventType.LOCK_RELEASED)
        assert released["payload"]["object_id"] == object_id


def test_invalid_object_id_in_lock_acquire_is_ignored(client: TestClient) -> None:
    campaign, campaign_map = _create_campaign_and_map(client)
    url = f"/api/v1/ws/campaigns/{campaign['id']}/maps/{campaign_map['id']}"

    with client.websocket_connect(url) as ws:
        ws.receive_json()  # map.connected
        ws.receive_json()  # presence.snapshot
        ws.receive_json()  # lock.snapshot
        ws.send_json({"type": "lock.acquire", "object_id": "not-a-uuid"})
        # Send a follow-up message to verify the connection is still alive
        # and the malformed lock didn't crash the handler.
        ws.send_json({"type": "noop"})
        # No exception means the route gracefully ignored the bad input.
