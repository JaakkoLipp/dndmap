from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.dependencies import StoreDependency, raise_not_found
from app.domain.models import MapAudience
from app.domain.schemas import LayerCreate, LayerRead, LayerUpdate

router = APIRouter(tags=["layers"])


@router.get("/maps/{map_id}/layers", response_model=list[LayerRead])
def list_layers(
    map_id: UUID,
    store: StoreDependency,
    visible: bool | None = None,
    audience: MapAudience | None = None,
) -> list:
    if store.get_map(map_id) is None:
        raise_not_found("Map")
    return list(store.list_layers(map_id=map_id, visible=visible, audience=audience))


@router.post(
    "/maps/{map_id}/layers",
    response_model=LayerRead,
    status_code=status.HTTP_201_CREATED,
)
def create_layer(map_id: UUID, payload: LayerCreate, store: StoreDependency):
    if store.get_map(map_id) is None:
        raise_not_found("Map")
    return store.create_layer(map_id=map_id, **payload.model_dump())


@router.get("/layers/{layer_id}", response_model=LayerRead)
def read_layer(layer_id: UUID, store: StoreDependency):
    layer = store.get_layer(layer_id)
    if layer is None:
        raise_not_found("Layer")
    return layer


@router.patch("/layers/{layer_id}", response_model=LayerRead)
def update_layer(layer_id: UUID, payload: LayerUpdate, store: StoreDependency):
    layer = store.update_layer(layer_id, payload.model_dump(exclude_unset=True))
    if layer is None:
        raise_not_found("Layer")
    return layer


@router.delete("/layers/{layer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_layer(layer_id: UUID, store: StoreDependency) -> Response:
    if not store.delete_layer(layer_id):
        raise_not_found("Layer")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
