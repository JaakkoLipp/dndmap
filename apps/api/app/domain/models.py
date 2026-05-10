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


class MapObjectKind(str, Enum):
    MARKER = "marker"
    LABEL = "label"
    LINE = "line"
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
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class Layer:
    map_id: UUID
    name: str
    kind: LayerKind = LayerKind.OBJECTS
    visible: bool = True
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
    x: float
    y: float
    width: float
    height: float
    rotation: float = 0.0
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
