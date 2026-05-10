from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from app.api.dependencies import StoreDependency, raise_not_found
from app.auth.dependencies import OptionalCurrentUser, get_campaign_member
from app.db import models as orm
from app.db.session import OptionalDbSession
from app.domain.models import MapAudience
from app.domain.schemas import MapObjectCreate, MapObjectRead, MapObjectUpdate

router = APIRouter(tags=["objects"])


@router.get("/maps/{map_id}/objects", response_model=list[MapObjectRead])
async def list_objects(
    map_id: UUID,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
    layer_id: UUID | None = None,
    visible: bool | None = None,
    audience: MapAudience | None = None,
) -> list:
    campaign_map = await store.get_map(map_id)
    if campaign_map is None:
        raise_not_found("Map")
    if user is not None:
        assert db is not None
        await get_campaign_member(campaign_map.campaign_id, user, db)
    if layer_id is not None:
        layer = await store.get_layer(layer_id)
        if layer is None or layer.map_id != map_id:
            raise_not_found("Layer")
    return await store.list_objects(
        map_id=map_id,
        layer_id=layer_id,
        visible=visible,
        audience=audience,
    )


@router.post(
    "/maps/{map_id}/objects",
    response_model=MapObjectRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_object(
    map_id: UUID,
    payload: MapObjectCreate,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
):
    campaign_map = await store.get_map(map_id)
    if campaign_map is None:
        raise_not_found("Map")
    if user is not None:
        assert db is not None
        await get_campaign_member(campaign_map.campaign_id, user, db, minimum_role=orm.CampaignRole.PLAYER)
    layer = await store.get_layer(payload.layer_id)
    if layer is None or layer.map_id != map_id:
        raise_not_found("Layer")
    return await store.create_object(map_id=map_id, **payload.to_store_values())


@router.get("/objects/{object_id}", response_model=MapObjectRead)
async def read_object(
    object_id: UUID,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
):
    map_object = await store.get_object(object_id)
    if map_object is None:
        raise_not_found("Object")
    if user is not None:
        assert db is not None
        campaign_map = await store.get_map(map_object.map_id)
        assert campaign_map is not None
        await get_campaign_member(campaign_map.campaign_id, user, db)
    return map_object


@router.patch("/objects/{object_id}", response_model=MapObjectRead)
async def update_object(
    object_id: UUID,
    payload: MapObjectUpdate,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
):
    current = await store.get_object(object_id)
    if current is None:
        raise_not_found("Object")
    if user is not None:
        assert db is not None
        campaign_map = await store.get_map(current.map_id)
        assert campaign_map is not None
        await get_campaign_member(campaign_map.campaign_id, user, db, minimum_role=orm.CampaignRole.PLAYER)

    try:
        changes = payload.to_store_changes(current)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if "layer_id" in changes:
        layer = await store.get_layer(changes["layer_id"])
        if layer is None or layer.map_id != current.map_id:
            raise_not_found("Layer")

    updated = await store.update_object(object_id, changes)
    if updated is None:
        raise_not_found("Object")
    return updated


@router.delete("/objects/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_object(
    object_id: UUID,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
) -> Response:
    map_object = await store.get_object(object_id)
    if map_object is None:
        raise_not_found("Object")
    if user is not None:
        assert db is not None
        campaign_map = await store.get_map(map_object.map_id)
        assert campaign_map is not None
        await get_campaign_member(campaign_map.campaign_id, user, db, minimum_role=orm.CampaignRole.DM)
    if not await store.delete_object(object_id):
        raise_not_found("Object")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
