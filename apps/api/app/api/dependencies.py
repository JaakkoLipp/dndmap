from typing import Annotated

from fastapi import Depends, HTTPException, Request, WebSocket, status

from app.core.config import Settings
from app.repositories.base import MapDataStore
from app.storage import ObjectStorage, S3ObjectStorage


def get_store(request: Request) -> MapDataStore:
    return request.app.state.store


def get_ws_store(websocket: WebSocket) -> MapDataStore:
    return websocket.app.state.store


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_storage(request: Request) -> ObjectStorage:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        storage = S3ObjectStorage(request.app.state.settings)
        request.app.state.storage = storage
    return storage


StoreDependency = Annotated[MapDataStore, Depends(get_store)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
StorageDependency = Annotated[ObjectStorage, Depends(get_storage)]


def raise_not_found(resource: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} not found",
    )
