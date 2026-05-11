from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.dependencies import StoreDependency, raise_not_found
from app.auth.dependencies import OptionalCurrentUser, get_campaign_member
from app.core.rate_limit import MutationRateLimit
from app.db import models as orm
from app.db.session import OptionalDbSession
from app.domain.models import MapAudience
from app.domain.schemas import MapObjectCreate, MapObjectRead, MapObjectUpdate
from app.realtime import EventType, actor_from_user, publish_event, write_revision

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
        if db is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not configured")
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
    request: Request,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
    _limit: MutationRateLimit = None,
):
    campaign_map = await store.get_map(map_id)
    if campaign_map is None:
        raise_not_found("Map")
    if user is not None:
        if db is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not configured")
        await get_campaign_member(campaign_map.campaign_id, user, db, minimum_role=orm.CampaignRole.PLAYER)
    layer = await store.get_layer(payload.layer_id)
    if layer is None or layer.map_id != map_id:
        raise_not_found("Layer")
    map_object = await store.create_object(map_id=map_id, **payload.to_store_values())
    event_payload = {
        "object_id": str(map_object.id),
        "layer_id": str(map_object.layer_id),
        "kind": map_object.kind.value,
        "name": map_object.name,
    }
    await publish_event(
        request,
        map_id,
        EventType.OBJECT_CREATED,
        actor=actor_from_user(user),
        payload=event_payload,
    )
    await write_revision(
        db,
        map_id=map_id,
        event_type=EventType.OBJECT_CREATED,
        actor=user,
        summary=f"Created {map_object.kind.value} \"{map_object.name}\"",
        payload=event_payload,
    )
    return map_object


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
        if db is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not configured")
        campaign_map = await store.get_map(map_object.map_id)
        if campaign_map is None:
            raise_not_found("Map")
        await get_campaign_member(campaign_map.campaign_id, user, db)
    return map_object


@router.patch("/objects/{object_id}", response_model=MapObjectRead)
async def update_object(
    object_id: UUID,
    payload: MapObjectUpdate,
    request: Request,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
    _limit: MutationRateLimit = None,
):
    current = await store.get_object(object_id)
    if current is None:
        raise_not_found("Object")
    if user is not None:
        if db is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not configured")
        campaign_map = await store.get_map(current.map_id)
        if campaign_map is None:
            raise_not_found("Map")
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
    event_payload = {
        "object_id": str(object_id),
        "layer_id": str(updated.layer_id),
        "fields": sorted(changes.keys()),
    }
    await publish_event(
        request,
        updated.map_id,
        EventType.OBJECT_UPDATED,
        actor=actor_from_user(user),
        payload=event_payload,
    )
    await write_revision(
        db,
        map_id=updated.map_id,
        event_type=EventType.OBJECT_UPDATED,
        actor=user,
        summary=f"Updated \"{updated.name}\"",
        payload=event_payload,
    )
    return updated


@router.delete("/objects/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_object(
    object_id: UUID,
    request: Request,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
    _limit: MutationRateLimit = None,
) -> Response:
    map_object = await store.get_object(object_id)
    if map_object is None:
        raise_not_found("Object")
    if user is not None:
        if db is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not configured")
        campaign_map = await store.get_map(map_object.map_id)
        if campaign_map is None:
            raise_not_found("Map")
        await get_campaign_member(campaign_map.campaign_id, user, db, minimum_role=orm.CampaignRole.DM)
    map_id = map_object.map_id
    layer_id = map_object.layer_id
    object_name = map_object.name
    if not await store.delete_object(object_id):
        raise_not_found("Object")
    event_payload = {
        "object_id": str(object_id),
        "layer_id": str(layer_id),
        "name": object_name,
    }
    await publish_event(
        request,
        map_id,
        EventType.OBJECT_DELETED,
        actor=actor_from_user(user),
        payload=event_payload,
    )
    await write_revision(
        db,
        map_id=map_id,
        event_type=EventType.OBJECT_DELETED,
        actor=user,
        summary=f"Deleted \"{object_name}\"",
        payload=event_payload,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
