from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.models import (
    ExportFormat,
    ExportStatus,
    LayerKind,
    MapAudience,
    MapObjectKind,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


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
    role: str | None = None


class Point(ApiModel):
    x: float
    y: float


class MarkerGeometry(ApiModel):
    type: Literal["marker"] = "marker"
    x: float
    y: float
    radius: float = Field(gt=0)


class LabelGeometry(ApiModel):
    type: Literal["label"] = "label"
    x: float
    y: float
    text: str = Field(default="", max_length=500)


class LineGeometry(ApiModel):
    type: Literal["polyline"] = "polyline"
    points: list[Point] = Field(min_length=2, max_length=2)


class FreehandGeometry(ApiModel):
    type: Literal["freehand"] = "freehand"
    points: list[Point] = Field(min_length=2)


class PolygonGeometry(ApiModel):
    type: Literal["polygon"] = "polygon"
    points: list[Point] = Field(min_length=3)


class HandoutGeometry(ApiModel):
    type: Literal["handout"] = "handout"
    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)


AnnotationGeometry = Annotated[
    MarkerGeometry
    | LabelGeometry
    | LineGeometry
    | FreehandGeometry
    | PolygonGeometry
    | HandoutGeometry,
    Field(discriminator="type"),
]


class AnnotationStyle(ApiModel):
    color: str | None = Field(default=None, min_length=1, max_length=32)
    fill_color: str | None = Field(
        default=None,
        validation_alias="fillColor",
        min_length=1,
        max_length=32,
    )
    stroke_color: str | None = Field(
        default=None,
        validation_alias="strokeColor",
        min_length=1,
        max_length=32,
    )
    border_color: str | None = Field(
        default=None,
        validation_alias="borderColor",
        min_length=1,
        max_length=32,
    )
    stroke_width: float | None = Field(
        default=None,
        validation_alias="strokeWidth",
        gt=0,
        le=256,
    )
    font_size: float | None = Field(
        default=None,
        validation_alias="fontSize",
        gt=0,
        le=512,
    )
    font_family: str | None = Field(
        default=None,
        validation_alias="fontFamily",
        min_length=1,
        max_length=120,
    )
    opacity: float | None = Field(default=None, ge=0.0, le=1.0)


def _kind_value(kind: MapObjectKind | str | None) -> str | None:
    if kind is None:
        return None
    if isinstance(kind, MapObjectKind):
        return kind.value
    return str(kind)


def _float_or(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _positive_float_or(value: Any, default: float) -> float:
    return max(_float_or(value, default), 0.01)


def _dump_geometry(geometry: Any) -> dict[str, Any] | None:
    if geometry is None:
        return None
    if isinstance(geometry, BaseModel):
        return geometry.model_dump(mode="json")
    return dict(geometry)


def _dump_style(style: Any) -> dict[str, Any] | None:
    if style is None:
        return None
    if isinstance(style, BaseModel):
        return style.model_dump(mode="json", exclude_none=True)
    return {key: value for key, value in dict(style).items() if value is not None}


def _dump_points(value: Any) -> list[dict[str, float]]:
    if not isinstance(value, list):
        return []

    points: list[dict[str, float]] = []
    for point in value:
        if isinstance(point, BaseModel):
            point_data = point.model_dump(mode="json")
        elif isinstance(point, dict):
            point_data = point
        else:
            continue

        if "x" not in point_data or "y" not in point_data:
            continue
        points.append(
            {
                "x": _float_or(point_data["x"], 0.0),
                "y": _float_or(point_data["y"], 0.0),
            }
        )

    return points


def _legacy_style_value(properties: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in properties and properties[key] is not None:
            return properties[key]
    return None


def _style_from_legacy(properties: dict[str, Any] | None) -> dict[str, Any] | None:
    properties = properties or {}
    style: dict[str, Any] = {}

    for target, aliases in {
        "color": ("color",),
        "fill_color": ("fill_color", "fillColor"),
        "stroke_color": ("stroke_color", "strokeColor"),
        "border_color": ("border_color", "borderColor"),
        "font_family": ("font_family", "fontFamily"),
    }.items():
        value = _legacy_style_value(properties, *aliases)
        if value is not None:
            style[target] = str(value)

    for target, aliases in {
        "stroke_width": ("stroke_width", "strokeWidth"),
        "font_size": ("font_size", "fontSize"),
        "opacity": ("opacity",),
    }.items():
        value = _legacy_style_value(properties, *aliases)
        if value is not None:
            style[target] = _float_or(value, 0.0)

    return style or None


def _geometry_from_legacy(
    kind: MapObjectKind | str,
    x: float | None,
    y: float | None,
    width: float | None,
    height: float | None,
    properties: dict[str, Any] | None,
) -> dict[str, Any]:
    kind_value = _kind_value(kind) or MapObjectKind.MARKER.value
    properties = properties or {}
    x_value = _float_or(x, 0.0)
    y_value = _float_or(y, 0.0)
    width_value = _positive_float_or(width, 1.0)
    height_value = _positive_float_or(height, 1.0)

    if kind_value == MapObjectKind.MARKER.value:
        radius = _positive_float_or(
            properties.get("radius"),
            max(width_value, height_value) / 2,
        )
        return {"type": kind_value, "x": x_value, "y": y_value, "radius": radius}

    if kind_value == MapObjectKind.LABEL.value:
        text = str(properties.get("text") or properties.get("label") or "")
        return {"type": kind_value, "x": x_value, "y": y_value, "text": text}

    if kind_value in {MapObjectKind.POLYLINE.value, MapObjectKind.FREEHAND.value}:
        points = _dump_points(properties.get("points"))
        if len(points) < 2:
            points = [
                {"x": x_value, "y": y_value},
                {"x": x_value + width_value, "y": y_value + height_value},
            ]
        if kind_value == MapObjectKind.POLYLINE.value:
            points = points[:2]
        return {"type": kind_value, "points": points}

    if kind_value == MapObjectKind.POLYGON.value:
        points = _dump_points(properties.get("points"))
        if len(points) < 3:
            points = [
                {"x": x_value, "y": y_value},
                {"x": x_value + width_value, "y": y_value},
                {"x": x_value + width_value, "y": y_value + height_value},
                {"x": x_value, "y": y_value + height_value},
            ]
        return {"type": kind_value, "points": points}

    if kind_value == MapObjectKind.HANDOUT.value:
        return {
            "type": kind_value,
            "x": x_value,
            "y": y_value,
            "width": width_value,
            "height": height_value,
        }

    return {"type": MapObjectKind.MARKER.value, "x": x_value, "y": y_value, "radius": 1}


def _bounds_from_geometry(
    geometry: dict[str, Any] | None,
    style: dict[str, Any] | None = None,
) -> dict[str, float]:
    if geometry is None:
        return {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}

    geometry_type = geometry.get("type")
    if geometry_type == MapObjectKind.MARKER.value:
        radius = _positive_float_or(geometry.get("radius"), 1.0)
        return {
            "x": _float_or(geometry.get("x"), 0.0),
            "y": _float_or(geometry.get("y"), 0.0),
            "width": radius * 2,
            "height": radius * 2,
        }

    if geometry_type == MapObjectKind.LABEL.value:
        font_size = _positive_float_or((style or {}).get("font_size"), 16.0)
        text = str(geometry.get("text") or "")
        return {
            "x": _float_or(geometry.get("x"), 0.0),
            "y": _float_or(geometry.get("y"), 0.0),
            "width": max(len(text) * font_size * 0.55, 1.0),
            "height": font_size,
        }

    if geometry_type == MapObjectKind.HANDOUT.value:
        return {
            "x": _float_or(geometry.get("x"), 0.0),
            "y": _float_or(geometry.get("y"), 0.0),
            "width": _positive_float_or(geometry.get("width"), 1.0),
            "height": _positive_float_or(geometry.get("height"), 1.0),
        }

    points = _dump_points(geometry.get("points"))
    if not points:
        return {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}

    xs = [point["x"] for point in points]
    ys = [point["y"] for point in points]
    min_x = min(xs)
    min_y = min(ys)
    return {
        "x": min_x,
        "y": min_y,
        "width": max(max(xs) - min_x, 1.0),
        "height": max(max(ys) - min_y, 1.0),
    }


def _geometry_with_legacy_changes(
    current_geometry: dict[str, Any] | None,
    changes: dict[str, Any],
    current: Any,
) -> dict[str, Any] | None:
    geometry = _dump_geometry(current_geometry)
    if geometry is None:
        return None

    geometry_type = geometry.get("type")
    if geometry_type in {MapObjectKind.MARKER.value, MapObjectKind.LABEL.value}:
        for field_name in ("x", "y"):
            if field_name in changes and changes[field_name] is not None:
                geometry[field_name] = _float_or(changes[field_name], 0.0)

        if geometry_type == MapObjectKind.MARKER.value:
            width = changes.get("width", getattr(current, "width", None))
            height = changes.get("height", getattr(current, "height", None))
            if width is not None or height is not None:
                geometry["radius"] = max(
                    _positive_float_or(width, 1.0),
                    _positive_float_or(height, 1.0),
                ) / 2
        return geometry

    if geometry_type == MapObjectKind.HANDOUT.value:
        for field_name in ("x", "y", "width", "height"):
            if field_name in changes and changes[field_name] is not None:
                geometry[field_name] = _float_or(changes[field_name], 0.0)
        return geometry

    if geometry_type in {
        MapObjectKind.POLYLINE.value,
        MapObjectKind.FREEHAND.value,
        MapObjectKind.POLYGON.value,
    }:
        dx = (
            _float_or(changes["x"], getattr(current, "x", 0.0))
            - _float_or(getattr(current, "x", 0.0), 0.0)
            if "x" in changes and changes["x"] is not None
            else 0.0
        )
        dy = (
            _float_or(changes["y"], getattr(current, "y", 0.0))
            - _float_or(getattr(current, "y", 0.0), 0.0)
            if "y" in changes and changes["y"] is not None
            else 0.0
        )
        if dx or dy:
            geometry["points"] = [
                {"x": point["x"] + dx, "y": point["y"] + dy}
                for point in _dump_points(geometry.get("points"))
            ]
        return geometry

    return geometry


def _ensure_geometry_kind(kind: MapObjectKind | str | None, geometry: Any) -> None:
    geometry_data = _dump_geometry(geometry)
    kind_value = _kind_value(kind)
    if geometry_data is None or kind_value is None:
        return
    if geometry_data.get("type") != kind_value:
        raise ValueError("geometry.type must match kind")


class MapCreate(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    width: int = Field(gt=0, le=100_000)
    height: int = Field(gt=0, le=100_000)
    grid_size: int = Field(default=70, gt=0, le=500)
    background_color: str = Field(default="#1f2937", min_length=1, max_length=32)
    image_object_key: str | None = Field(
        default=None,
        validation_alias="imageObjectKey",
        max_length=1024,
    )
    image_url: str | None = Field(
        default=None,
        validation_alias="imageUrl",
        max_length=2048,
    )
    image_name: str | None = Field(
        default=None,
        validation_alias="imageName",
        max_length=255,
    )
    image_content_type: str | None = Field(
        default=None,
        validation_alias="imageContentType",
        max_length=120,
    )


class MapUpdate(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    width: int | None = Field(default=None, gt=0, le=100_000)
    height: int | None = Field(default=None, gt=0, le=100_000)
    grid_size: int | None = Field(default=None, gt=0, le=500)
    background_color: str | None = Field(default=None, min_length=1, max_length=32)
    image_object_key: str | None = Field(
        default=None,
        validation_alias="imageObjectKey",
        max_length=1024,
    )
    image_url: str | None = Field(
        default=None,
        validation_alias="imageUrl",
        max_length=2048,
    )
    image_name: str | None = Field(
        default=None,
        validation_alias="imageName",
        max_length=255,
    )
    image_content_type: str | None = Field(
        default=None,
        validation_alias="imageContentType",
        max_length=120,
    )


class MapRead(ApiModel):
    id: UUID
    campaign_id: UUID
    name: str
    width: int
    height: int
    grid_size: int
    background_color: str
    image_object_key: str | None
    image_url: str | None
    image_name: str | None
    image_content_type: str | None
    created_at: datetime
    updated_at: datetime


class LayerCreate(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    kind: LayerKind = LayerKind.OBJECTS
    visible: bool = True
    audience: MapAudience = MapAudience.ALL
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    sort_order: int = 0


class LayerUpdate(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: LayerKind | None = None
    visible: bool | None = None
    audience: MapAudience | None = None
    opacity: float | None = Field(default=None, ge=0.0, le=1.0)
    sort_order: int | None = None


class LayerRead(ApiModel):
    id: UUID
    map_id: UUID
    name: str
    kind: LayerKind
    visible: bool
    audience: MapAudience
    opacity: float
    sort_order: int
    created_at: datetime
    updated_at: datetime


class MapObjectCreate(ApiModel):
    layer_id: UUID
    name: str = Field(min_length=1, max_length=120)
    kind: MapObjectKind = MapObjectKind.MARKER
    x: float | None = None
    y: float | None = None
    width: float | None = Field(default=None, gt=0)
    height: float | None = Field(default=None, gt=0)
    rotation: float = 0.0
    visible: bool = True
    audience: MapAudience = MapAudience.ALL
    geometry: AnnotationGeometry | None = None
    style: AnnotationStyle | None = None
    properties: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def infer_kind_from_geometry(cls, data: Any) -> Any:
        if not isinstance(data, dict) or data.get("kind") is not None:
            return data

        geometry = data.get("geometry")
        if isinstance(geometry, dict) and geometry.get("type") is not None:
            return {**data, "kind": geometry["type"]}
        return data

    @model_validator(mode="after")
    def validate_geometry_kind(self) -> "MapObjectCreate":
        _ensure_geometry_kind(self.kind, self.geometry)
        return self

    def to_store_values(self) -> dict[str, Any]:
        values = self.model_dump(
            exclude={"geometry", "style"},
            exclude_none=True,
        )
        style = (
            _dump_style(self.style)
            if self.style is not None
            else _style_from_legacy(self.properties)
        )
        geometry = (
            _dump_geometry(self.geometry)
            if self.geometry is not None
            else _geometry_from_legacy(
                self.kind,
                self.x,
                self.y,
                self.width,
                self.height,
                self.properties,
            )
        )
        bounds = _bounds_from_geometry(geometry, style)

        for field_name, value in bounds.items():
            values.setdefault(field_name, value)
        values["geometry"] = geometry
        if style is not None:
            values["style"] = style
        return values


class MapObjectUpdate(ApiModel):
    layer_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: MapObjectKind | None = None
    x: float | None = None
    y: float | None = None
    width: float | None = Field(default=None, gt=0)
    height: float | None = Field(default=None, gt=0)
    rotation: float | None = None
    visible: bool | None = None
    audience: MapAudience | None = None
    geometry: AnnotationGeometry | None = None
    style: AnnotationStyle | None = None
    properties: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_geometry_kind(self) -> "MapObjectUpdate":
        if self.kind is not None and self.geometry is not None:
            _ensure_geometry_kind(self.kind, self.geometry)
        return self

    def to_store_changes(self, current: Any) -> dict[str, Any]:
        changes = self.model_dump(
            exclude={"geometry", "style"},
            exclude_unset=True,
        )

        if "style" in self.model_fields_set:
            changes["style"] = _dump_style(self.style)

        if "geometry" in self.model_fields_set:
            geometry = _dump_geometry(self.geometry)
            candidate_kind = changes.get("kind", getattr(current, "kind", None))
            _ensure_geometry_kind(candidate_kind, geometry)
            changes["geometry"] = geometry

            if geometry is not None:
                bounds = _bounds_from_geometry(geometry, changes.get("style"))
                for field_name, value in bounds.items():
                    if changes.get(field_name) is None:
                        changes[field_name] = value
        elif any(field_name in changes for field_name in ("x", "y", "width", "height")):
            current_geometry = getattr(current, "geometry", None)
            geometry = _geometry_with_legacy_changes(current_geometry, changes, current)
            if geometry is not None:
                changes["geometry"] = geometry

        if "kind" in changes and "geometry" not in changes:
            geometry = _geometry_from_legacy(
                changes["kind"],
                changes.get("x", getattr(current, "x", None)),
                changes.get("y", getattr(current, "y", None)),
                changes.get("width", getattr(current, "width", None)),
                changes.get("height", getattr(current, "height", None)),
                changes.get("properties", getattr(current, "properties", None)),
            )
            changes["geometry"] = geometry
            bounds = _bounds_from_geometry(geometry, changes.get("style"))
            for field_name, value in bounds.items():
                if changes.get(field_name) is None:
                    changes[field_name] = value

        return changes


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
    visible: bool
    audience: MapAudience
    geometry: AnnotationGeometry | None
    style: AnnotationStyle | None
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


# --- Auth schemas ---

class UserRead(ApiModel):
    id: UUID
    display_name: str
    avatar_url: str | None
    created_at: datetime


class InviteCreate(ApiModel):
    role: str = Field(default="player", pattern=r"^(owner|dm|player|viewer)$")
    max_uses: int | None = Field(default=None, gt=0)
    expires_in_hours: int | None = Field(default=None, gt=0, le=720)


class InviteRead(ApiModel):
    id: UUID
    campaign_id: UUID
    code: str
    role: str
    max_uses: int | None
    use_count: int
    expires_at: datetime | None
    created_at: datetime


class CampaignMemberRead(ApiModel):
    campaign_id: UUID
    user_id: UUID
    role: str
    joined_at: datetime


class CampaignMemberDetail(ApiModel):
    """Members listing payload — joined with the user record for display."""

    campaign_id: UUID
    user_id: UUID
    role: str
    joined_at: datetime
    display_name: str
    avatar_url: str | None


class CampaignMemberUpdate(ApiModel):
    role: Literal["owner", "dm", "player", "viewer"]
