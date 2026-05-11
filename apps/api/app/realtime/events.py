"""Realtime event envelope and well-known event types.

All WebSocket payloads emitted by the server share the envelope shape:

    {
      "id": str,            # uuid4, unique per event
      "type": str,          # see EventType
      "map_id": str,        # uuid of the map the event concerns
      "actor": Actor | None,# who triggered the event (None for system events)
      "payload": dict,      # event-specific data
      "sent_at": str        # ISO-8601 timestamp
    }

REST routes mutate state, then publish an envelope via ``publish_event``.
Connected clients receive envelopes and decide whether to refetch data.
"""

from __future__ import annotations

from typing import Any, TypedDict
from uuid import UUID, uuid4

from fastapi.encoders import jsonable_encoder

from app.domain.models import utc_now


class EventType:
    """Stable string identifiers for outbound WebSocket events."""

    MAP_CONNECTED = "map.connected"

    PRESENCE_SNAPSHOT = "presence.snapshot"
    PRESENCE_JOINED = "presence.joined"
    PRESENCE_LEFT = "presence.left"

    MAP_UPDATED = "map.updated"
    MAP_IMAGE_UPDATED = "map.image_updated"
    MAP_DELETED = "map.deleted"

    LAYER_CREATED = "layer.created"
    LAYER_UPDATED = "layer.updated"
    LAYER_DELETED = "layer.deleted"

    OBJECT_CREATED = "object.created"
    OBJECT_UPDATED = "object.updated"
    OBJECT_DELETED = "object.deleted"

    LOCK_ACQUIRED = "lock.acquired"
    LOCK_RELEASED = "lock.released"
    LOCK_DENIED = "lock.denied"
    LOCK_SNAPSHOT = "lock.snapshot"


class Actor(TypedDict, total=False):
    user_id: str
    display_name: str
    role: str
    client_id: str


def build_envelope(
    event_type: str,
    map_id: UUID,
    *,
    actor: Actor | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable event envelope."""
    return jsonable_encoder(
        {
            "id": str(uuid4()),
            "type": event_type,
            "map_id": str(map_id),
            "actor": actor,
            "payload": payload or {},
            "sent_at": utc_now(),
        }
    )
