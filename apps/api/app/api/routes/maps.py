from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.dependencies import StoreDependency, raise_not_found
from app.domain.schemas import MapCreate, MapRead, MapUpdate

router = APIRouter(tags=["maps"])


@router.get("/campaigns/{campaign_id}/maps", response_model=list[MapRead])
def list_maps(campaign_id: UUID, store: StoreDependency) -> list:
    if store.get_campaign(campaign_id) is None:
        raise_not_found("Campaign")
    return list(store.list_maps(campaign_id=campaign_id))


@router.post(
    "/campaigns/{campaign_id}/maps",
    response_model=MapRead,
    status_code=status.HTTP_201_CREATED,
)
def create_map(campaign_id: UUID, payload: MapCreate, store: StoreDependency):
    if store.get_campaign(campaign_id) is None:
        raise_not_found("Campaign")
    return store.create_map(campaign_id=campaign_id, **payload.model_dump())


@router.get("/maps/{map_id}", response_model=MapRead)
def read_map(map_id: UUID, store: StoreDependency):
    campaign_map = store.get_map(map_id)
    if campaign_map is None:
        raise_not_found("Map")
    return campaign_map


@router.patch("/maps/{map_id}", response_model=MapRead)
def update_map(map_id: UUID, payload: MapUpdate, store: StoreDependency):
    campaign_map = store.update_map(
        map_id,
        payload.model_dump(exclude_unset=True),
    )
    if campaign_map is None:
        raise_not_found("Map")
    return campaign_map


@router.delete("/maps/{map_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_map(map_id: UUID, store: StoreDependency) -> Response:
    if not store.delete_map(map_id):
        raise_not_found("Map")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

