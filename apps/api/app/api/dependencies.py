from typing import Annotated

from fastapi import Depends, HTTPException, Request, WebSocket, status

from app.core.config import Settings
from app.repositories.base import MapDataStore


def get_store(request: Request) -> MapDataStore:
    return request.app.state.store


def get_ws_store(websocket: WebSocket) -> MapDataStore:
    return websocket.app.state.store


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


StoreDependency = Annotated[MapDataStore, Depends(get_store)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def raise_not_found(resource: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} not found",
    )
