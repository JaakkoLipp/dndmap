from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.dependencies import StoreDependency, raise_not_found
from app.auth.dependencies import OptionalCurrentUser, get_campaign_member
from app.db import models as orm
from app.db.session import OptionalDbSession
from app.domain.schemas import MapCreate, MapRead, MapUpdate

router = APIRouter(tags=["maps"])


@router.get("/campaigns/{campaign_id}/maps", response_model=list[MapRead])
async def list_maps(
    campaign_id: UUID,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
) -> list:
    if user is not None:
        assert db is not None
        await get_campaign_member(campaign_id, user, db)
    elif await store.get_campaign(campaign_id) is None:
        raise_not_found("Campaign")
    return await store.list_maps(campaign_id=campaign_id)


@router.post(
    "/campaigns/{campaign_id}/maps",
    response_model=MapRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_map(
    campaign_id: UUID,
    payload: MapCreate,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
):
    if user is not None:
        assert db is not None
        await get_campaign_member(campaign_id, user, db, minimum_role=orm.CampaignRole.DM)
    elif await store.get_campaign(campaign_id) is None:
        raise_not_found("Campaign")
    return await store.create_map(campaign_id=campaign_id, **payload.model_dump())


@router.get("/maps/{map_id}", response_model=MapRead)
async def read_map(
    map_id: UUID,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
):
    campaign_map = await store.get_map(map_id)
    if campaign_map is None:
        raise_not_found("Map")
    if user is not None:
        assert db is not None
        await get_campaign_member(campaign_map.campaign_id, user, db)
    return campaign_map


@router.patch("/maps/{map_id}", response_model=MapRead)
async def update_map(
    map_id: UUID,
    payload: MapUpdate,
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
    updated = await store.update_map(map_id, payload.model_dump(exclude_unset=True))
    if updated is None:
        raise_not_found("Map")
    return updated


@router.delete("/maps/{map_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_map(
    map_id: UUID,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
) -> Response:
    campaign_map = await store.get_map(map_id)
    if campaign_map is None:
        raise_not_found("Map")
    if user is not None:
        assert db is not None
        await get_campaign_member(campaign_map.campaign_id, user, db, minimum_role=orm.CampaignRole.DM)
    if not await store.delete_map(map_id):
        raise_not_found("Map")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
