from uuid import UUID

from fastapi import APIRouter, status

from app.api.dependencies import StoreDependency, raise_not_found
from app.domain.schemas import ExportCreate, ExportJobRead

router = APIRouter(tags=["exports"])


@router.get("/maps/{map_id}/exports", response_model=list[ExportJobRead])
def list_exports(map_id: UUID, store: StoreDependency) -> list:
    if store.get_map(map_id) is None:
        raise_not_found("Map")
    return list(store.list_exports(map_id=map_id))


@router.post(
    "/maps/{map_id}/exports",
    response_model=ExportJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_export(map_id: UUID, payload: ExportCreate, store: StoreDependency):
    if store.get_map(map_id) is None:
        raise_not_found("Map")
    return store.create_export(map_id=map_id, **payload.model_dump())


@router.get("/exports/{export_id}", response_model=ExportJobRead)
def read_export(export_id: UUID, store: StoreDependency):
    export = store.get_export(export_id)
    if export is None:
        raise_not_found("Export")
    return export

