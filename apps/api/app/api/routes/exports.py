from uuid import UUID

from fastapi import APIRouter, status

from app.api.dependencies import StoreDependency, raise_not_found
from app.auth.dependencies import OptionalCurrentUser, get_campaign_member
from app.db import models as orm
from app.db.session import OptionalDbSession
from app.domain.schemas import ExportCreate, ExportJobRead

router = APIRouter(tags=["exports"])


@router.get("/maps/{map_id}/exports", response_model=list[ExportJobRead])
async def list_exports(
    map_id: UUID,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
) -> list:
    campaign_map = await store.get_map(map_id)
    if campaign_map is None:
        raise_not_found("Map")
    if user is not None:
        assert db is not None
        await get_campaign_member(campaign_map.campaign_id, user, db)
    return await store.list_exports(map_id=map_id)


@router.post(
    "/maps/{map_id}/exports",
    response_model=ExportJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_export(
    map_id: UUID,
    payload: ExportCreate,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
):
    campaign_map = await store.get_map(map_id)
    if campaign_map is None:
        raise_not_found("Map")
    if user is not None:
        assert db is not None
        await get_campaign_member(campaign_map.campaign_id, user, db, minimum_role=orm.CampaignRole.DM)
    return await store.create_export(map_id=map_id, **payload.model_dump())


@router.get("/exports/{export_id}", response_model=ExportJobRead)
async def read_export(
    export_id: UUID,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
):
    export = await store.get_export(export_id)
    if export is None:
        raise_not_found("Export")
    if user is not None:
        assert db is not None
        campaign_map = await store.get_map(export.map_id)
        assert campaign_map is not None
        await get_campaign_member(campaign_map.campaign_id, user, db)
    return export
