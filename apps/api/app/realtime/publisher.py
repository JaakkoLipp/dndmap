"""Helpers for REST routes to publish realtime events.

Routes import :func:`publish_event` and call it after persistence succeeds.
The publisher resolves the broker from ``request.app.state``; when realtime
is not configured (e.g. tests that don't run the lifespan) the call is a
no-op.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import Request

from app.db import models as orm
from app.realtime.events import Actor, build_envelope

logger = logging.getLogger(__name__)


def actor_from_user(
    user: orm.User | None, role: orm.CampaignRole | None = None
) -> Actor | None:
    if user is None:
        return None
    actor: Actor = {
        "user_id": str(user.id),
        "display_name": user.display_name,
    }
    if role is not None:
        actor["role"] = role.value
    return actor


async def publish_event(
    request: Request,
    map_id: UUID,
    event_type: str,
    *,
    actor: Actor | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    broker = getattr(request.app.state, "realtime_broker", None)
    if broker is None:
        return
    envelope = build_envelope(event_type, map_id, actor=actor, payload=payload)
    try:
        await broker.publish(map_id, envelope)
    except Exception:  # pragma: no cover - defensive
        logger.exception("Failed to publish realtime event %s", event_type)
