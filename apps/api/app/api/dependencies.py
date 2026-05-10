from typing import Annotated

from fastapi import Depends, HTTPException, Request, WebSocket, status

from app.core.config import Settings
from app.repositories.base import MapDataStore


def get_store(connection: Request | WebSocket) -> MapDataStore:
    return connection.app.state.store


def get_settings(connection: Request | WebSocket) -> Settings:
    return connection.app.state.settings


StoreDependency = Annotated[MapDataStore, Depends(get_store)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def raise_not_found(resource: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} not found",
    )
