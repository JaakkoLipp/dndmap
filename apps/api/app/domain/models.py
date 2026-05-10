from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class LayerKind(str, Enum):
    BACKGROUND = "background"
    TERRAIN = "terrain"
    OBJECTS = "objects"
    FOG = "fog"
    NOTES = "notes"


class MapAudience(str, Enum):
    DM = "dm"
    PLAYERS = "players"
    ALL = "all"


class MapObjectKind(str, Enum):
    MARKER = "marker"
    LABEL = "label"
    POLYLINE = "polyline"
    FREEHAND = "freehand"
    POLYGON = "polygon"
    HANDOUT = "handout"


class ExportFormat(str, Enum):
    JSON = "json"
    PNG = "png"
    PDF = "pdf"


class ExportStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class Campaign:
    name: str
    description: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class CampaignMap:
    campaign_id: UUID
    name: str
    width: int
    height: int
    grid_size: int
    background_color: str = "#1f2937"
    image_object_key: str | None = None
    image_url: str | None = None
    image_name: str | None = None
    image_content_type: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class Layer:
    map_id: UUID
    name: str
    kind: LayerKind = LayerKind.OBJECTS
    visible: bool = True
    audience: MapAudience = MapAudience.ALL
    opacity: float = 1.0
    sort_order: int = 0
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class MapObject:
    map_id: UUID
    layer_id: UUID
    name: str
    kind: MapObjectKind
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 1.0
    rotation: float = 0.0
    visible: bool = True
    audience: MapAudience = MapAudience.ALL
    geometry: dict[str, Any] | None = None
    style: dict[str, Any] | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class ExportJob:
    map_id: UUID
    format: ExportFormat
    include_hidden_layers: bool = False
    options: dict[str, Any] = field(default_factory=dict)
    status: ExportStatus = ExportStatus.QUEUED
    error: str | None = None
    download_url: str | None = None
    id: UUID = field(default_factory=uuid4)
    requested_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None
