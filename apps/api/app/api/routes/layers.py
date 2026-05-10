from uuid import UUID

from fastapi import APIRouter, Request, Response, status

from app.api.dependencies import StoreDependency, raise_not_found
from app.auth.dependencies import OptionalCurrentUser, get_campaign_member
from app.core.rate_limit import MutationRateLimit
from app.db import models as orm
from app.db.session import OptionalDbSession
from app.domain.models import MapAudience
from app.domain.schemas import LayerCreate, LayerRead, LayerUpdate
from app.realtime import EventType, actor_from_user, publish_event

router = APIRouter(tags=["layers"])


@router.get("/maps/{map_id}/layers", response_model=list[LayerRead])
async def list_layers(
    map_id: UUID,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
    visible: bool | None = None,
    audience: MapAudience | None = None,
) -> list:
    campaign_map = await store.get_map(map_id)
    if campaign_map is None:
        raise_not_found("Map")
    if user is not None:
        assert db is not None
        await get_campaign_member(campaign_map.campaign_id, user, db)
    return await store.list_layers(map_id=map_id, visible=visible, audience=audience)


@router.post(
    "/maps/{map_id}/layers",
    response_model=LayerRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_layer(
    map_id: UUID,
    payload: LayerCreate,
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
        assert db is not None
        await get_campaign_member(campaign_map.campaign_id, user, db, minimum_role=orm.CampaignRole.DM)
    layer = await store.create_layer(map_id=map_id, **payload.model_dump())
    await publish_event(
        request,
        map_id,
        EventType.LAYER_CREATED,
        actor=actor_from_user(user),
        payload={"layer_id": str(layer.id)},
    )
    return layer


@router.get("/layers/{layer_id}", response_model=LayerRead)
async def read_layer(
    layer_id: UUID,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
):
    layer = await store.get_layer(layer_id)
    if layer is None:
        raise_not_found("Layer")
    if user is not None:
        assert db is not None
        campaign_map = await store.get_map(layer.map_id)
        assert campaign_map is not None
        await get_campaign_member(campaign_map.campaign_id, user, db)
    return layer


@router.patch("/layers/{layer_id}", response_model=LayerRead)
async def update_layer(
    layer_id: UUID,
    payload: LayerUpdate,
    request: Request,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
    _limit: MutationRateLimit = None,
):
    layer = await store.get_layer(layer_id)
    if layer is None:
        raise_not_found("Layer")
    if user is not None:
        assert db is not None
        campaign_map = await store.get_map(layer.map_id)
        assert campaign_map is not None
        await get_campaign_member(campaign_map.campaign_id, user, db, minimum_role=orm.CampaignRole.DM)
    updated = await store.update_layer(layer_id, payload.model_dump(exclude_unset=True))
    if updated is None:
        raise_not_found("Layer")
    await publish_event(
        request,
        updated.map_id,
        EventType.LAYER_UPDATED,
        actor=actor_from_user(user),
        payload={"layer_id": str(layer_id)},
    )
    return updated


@router.delete("/layers/{layer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_layer(
    layer_id: UUID,
    request: Request,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
    _limit: MutationRateLimit = None,
) -> Response:
    layer = await store.get_layer(layer_id)
    if layer is None:
        raise_not_found("Layer")
    if user is not None:
        assert db is not None
        campaign_map = await store.get_map(layer.map_id)
        assert campaign_map is not None
        await get_campaign_member(campaign_map.campaign_id, user, db, minimum_role=orm.CampaignRole.DM)
    map_id = layer.map_id
    if not await store.delete_layer(layer_id):
        raise_not_found("Layer")
    await publish_event(
        request,
        map_id,
        EventType.LAYER_DELETED,
        actor=actor_from_user(user),
        payload={"layer_id": str(layer_id)},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
