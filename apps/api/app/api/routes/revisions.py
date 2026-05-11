"""Map revision history.

Append-only mutation log surfaced at ``GET /maps/{id}/revisions``. Writes
are produced inline by the mutation routes (objects, layers, maps) via
:func:`app.realtime.write_revision`; this endpoint is read-only.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.dependencies import StoreDependency, raise_not_found
from app.auth.dependencies import OptionalCurrentUser, get_campaign_member
from app.db import models as orm
from app.db.session import OptionalDbSession
from app.domain.schemas import MapRevisionRead

router = APIRouter(tags=["revisions"])


@router.get("/maps/{map_id}/revisions", response_model=list[MapRevisionRead])
async def list_revisions(
    map_id: UUID,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
    limit: int = Query(default=50, ge=1, le=200),
) -> list:
    campaign_map = await store.get_map(map_id)
    if campaign_map is None:
        raise_not_found("Map")
    if user is not None:
        if db is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not configured")
        await get_campaign_member(campaign_map.campaign_id, user, db)

    if db is None:
        # In-memory mode does not persist revisions.
        return []

    result = await db.execute(
        select(orm.MapRevision)
        .where(orm.MapRevision.map_id == map_id)
        .order_by(orm.MapRevision.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
