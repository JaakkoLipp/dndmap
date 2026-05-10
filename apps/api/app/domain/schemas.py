from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import ExportFormat, ExportStatus, LayerKind, MapObjectKind


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthRead(ApiModel):
    status: Literal["ok"]
    service: str
    version: str
    environment: str


class CampaignCreate(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)


class CampaignUpdate(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)


class CampaignRead(ApiModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class MapCreate(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    width: int = Field(gt=0, le=100_000)
    height: int = Field(gt=0, le=100_000)
    grid_size: int = Field(default=70, gt=0, le=500)
    background_color: str = Field(default="#1f2937", min_length=1, max_length=32)


class MapUpdate(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    width: int | None = Field(default=None, gt=0, le=100_000)
    height: int | None = Field(default=None, gt=0, le=100_000)
    grid_size: int | None = Field(default=None, gt=0, le=500)
    background_color: str | None = Field(default=None, min_length=1, max_length=32)


class MapRead(ApiModel):
    id: UUID
    campaign_id: UUID
    name: str
    width: int
    height: int
    grid_size: int
    background_color: str
    created_at: datetime
    updated_at: datetime


class LayerCreate(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    kind: LayerKind = LayerKind.OBJECTS
    visible: bool = True
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    sort_order: int = 0


class LayerUpdate(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: LayerKind | None = None
    visible: bool | None = None
    opacity: float | None = Field(default=None, ge=0.0, le=1.0)
    sort_order: int | None = None


class LayerRead(ApiModel):
    id: UUID
    map_id: UUID
    name: str
    kind: LayerKind
    visible: bool
    opacity: float
    sort_order: int
    created_at: datetime
    updated_at: datetime


class MapObjectCreate(ApiModel):
    layer_id: UUID
    name: str = Field(min_length=1, max_length=120)
    kind: MapObjectKind = MapObjectKind.MARKER
    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    rotation: float = 0.0
    properties: dict[str, Any] = Field(default_factory=dict)


class MapObjectUpdate(ApiModel):
    layer_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: MapObjectKind | None = None
    x: float | None = None
    y: float | None = None
    width: float | None = Field(default=None, gt=0)
    height: float | None = Field(default=None, gt=0)
    rotation: float | None = None
    properties: dict[str, Any] | None = None


class MapObjectRead(ApiModel):
    id: UUID
    map_id: UUID
    layer_id: UUID
    name: str
    kind: MapObjectKind
    x: float
    y: float
    width: float
    height: float
    rotation: float
    properties: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ExportCreate(ApiModel):
    format: ExportFormat = ExportFormat.JSON
    include_hidden_layers: bool = False
    options: dict[str, Any] = Field(default_factory=dict)


class ExportJobRead(ApiModel):
    id: UUID
    map_id: UUID
    format: ExportFormat
    include_hidden_layers: bool
    options: dict[str, Any]
    status: ExportStatus
    error: str | None
    download_url: str | None
    requested_at: datetime
    completed_at: datetime | None
