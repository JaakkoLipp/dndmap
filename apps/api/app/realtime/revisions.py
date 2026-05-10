"""Helpers to write map revision rows from REST mutation handlers.

Each successful mutation should publish a realtime event *and* write a
revision row. The two live next to each other in ``app.realtime`` because
they share the same envelope shape and actor concept; the revision write
is best-effort and silently skipped when the database is not configured
(in-memory test mode).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as orm

logger = logging.getLogger(__name__)


async def write_revision(
    db: AsyncSession | None,
    *,
    map_id: UUID,
    event_type: str,
    actor: orm.User | None = None,
    summary: str = "",
    payload: dict[str, Any] | None = None,
) -> None:
    if db is None:
        return
    try:
        revision = orm.MapRevision(
            map_id=map_id,
            actor_user_id=actor.id if actor else None,
            actor_display_name=actor.display_name if actor else None,
            event_type=event_type,
            summary=summary,
            payload=payload or {},
        )
        db.add(revision)
        await db.commit()
    except Exception:  # pragma: no cover - defensive
        logger.exception("Failed to write map revision for %s", event_type)
