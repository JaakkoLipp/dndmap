from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from app.api.dependencies import StoreDependency, raise_not_found
from app.domain.models import MapAudience
from app.domain.schemas import MapObjectCreate, MapObjectRead, MapObjectUpdate

router = APIRouter(tags=["objects"])


@router.get("/maps/{map_id}/objects", response_model=list[MapObjectRead])
def list_objects(
    map_id: UUID,
    store: StoreDependency,
    layer_id: UUID | None = None,
    visible: bool | None = None,
    audience: MapAudience | None = None,
) -> list:
    if store.get_map(map_id) is None:
        raise_not_found("Map")
    if layer_id is not None:
        layer = store.get_layer(layer_id)
        if layer is None or layer.map_id != map_id:
            raise_not_found("Layer")
    return list(
        store.list_objects(
            map_id=map_id,
            layer_id=layer_id,
            visible=visible,
            audience=audience,
        )
    )


@router.post(
    "/maps/{map_id}/objects",
    response_model=MapObjectRead,
    status_code=status.HTTP_201_CREATED,
)
def create_object(map_id: UUID, payload: MapObjectCreate, store: StoreDependency):
    if store.get_map(map_id) is None:
        raise_not_found("Map")
    layer = store.get_layer(payload.layer_id)
    if layer is None or layer.map_id != map_id:
        raise_not_found("Layer")
    return store.create_object(map_id=map_id, **payload.to_store_values())


@router.get("/objects/{object_id}", response_model=MapObjectRead)
def read_object(object_id: UUID, store: StoreDependency):
    map_object = store.get_object(object_id)
    if map_object is None:
        raise_not_found("Object")
    return map_object


@router.patch("/objects/{object_id}", response_model=MapObjectRead)
def update_object(
    object_id: UUID,
    payload: MapObjectUpdate,
    store: StoreDependency,
):
    current = store.get_object(object_id)
    if current is None:
        raise_not_found("Object")

    try:
        changes = payload.to_store_changes(current)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if "layer_id" in changes:
        layer = store.get_layer(changes["layer_id"])
        if layer is None or layer.map_id != current.map_id:
            raise_not_found("Layer")

    updated = store.update_object(object_id, changes)
    if updated is None:
        raise_not_found("Object")
    return updated


@router.delete("/objects/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_object(object_id: UUID, store: StoreDependency) -> Response:
    if not store.delete_object(object_id):
        raise_not_found("Object")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
