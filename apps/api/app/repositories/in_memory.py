from collections.abc import Mapping, Sequence
from threading import RLock
from typing import Any
from uuid import UUID

from app.domain.models import (
    Campaign,
    CampaignMap,
    ExportJob,
    Layer,
    MapAudience,
    MapObject,
    utc_now,
)


class InMemoryMapStore:
    """Small repository adapter for local development and tests."""

    def __init__(self) -> None:
        self._campaigns: dict[UUID, Campaign] = {}
        self._maps: dict[UUID, CampaignMap] = {}
        self._layers: dict[UUID, Layer] = {}
        self._objects: dict[UUID, MapObject] = {}
        self._exports: dict[UUID, ExportJob] = {}
        self._lock = RLock()

    def list_campaigns(self) -> Sequence[Campaign]:
        with self._lock:
            return sorted(self._campaigns.values(), key=lambda item: item.created_at)

    def create_campaign(self, name: str, description: str | None = None) -> Campaign:
        with self._lock:
            campaign = Campaign(name=name, description=description)
            self._campaigns[campaign.id] = campaign
            return campaign

    def get_campaign(self, campaign_id: UUID) -> Campaign | None:
        with self._lock:
            return self._campaigns.get(campaign_id)

    def update_campaign(
        self,
        campaign_id: UUID,
        changes: Mapping[str, Any],
    ) -> Campaign | None:
        with self._lock:
            campaign = self._campaigns.get(campaign_id)
            if campaign is None:
                return None
            return self._apply_changes(campaign, changes)

    def delete_campaign(self, campaign_id: UUID) -> bool:
        with self._lock:
            if campaign_id not in self._campaigns:
                return False

            map_ids = [
                map_id
                for map_id, campaign_map in self._maps.items()
                if campaign_map.campaign_id == campaign_id
            ]
            for map_id in map_ids:
                self._delete_map_cascade(map_id)
            del self._campaigns[campaign_id]
            return True

    def list_maps(self, campaign_id: UUID | None = None) -> Sequence[CampaignMap]:
        with self._lock:
            maps = self._maps.values()
            if campaign_id is not None:
                maps = [item for item in maps if item.campaign_id == campaign_id]
            return sorted(maps, key=lambda item: item.created_at)

    def create_map(self, campaign_id: UUID, **values: Any) -> CampaignMap:
        with self._lock:
            campaign_map = CampaignMap(campaign_id=campaign_id, **values)
            self._maps[campaign_map.id] = campaign_map
            return campaign_map

    def get_map(self, map_id: UUID) -> CampaignMap | None:
        with self._lock:
            return self._maps.get(map_id)

    def update_map(
        self,
        map_id: UUID,
        changes: Mapping[str, Any],
    ) -> CampaignMap | None:
        with self._lock:
            campaign_map = self._maps.get(map_id)
            if campaign_map is None:
                return None
            return self._apply_changes(campaign_map, changes)

    def delete_map(self, map_id: UUID) -> bool:
        with self._lock:
            if map_id not in self._maps:
                return False
            self._delete_map_cascade(map_id)
            return True

    def list_layers(
        self,
        map_id: UUID | None = None,
        visible: bool | None = None,
        audience: MapAudience | None = None,
    ) -> Sequence[Layer]:
        with self._lock:
            layers = self._layers.values()
            if map_id is not None:
                layers = [item for item in layers if item.map_id == map_id]
            if visible is not None:
                layers = [item for item in layers if item.visible is visible]
            if audience is not None:
                layers = [
                    item
                    for item in layers
                    if _audience_value(item.audience) == _audience_value(audience)
                ]
            return sorted(layers, key=lambda item: (item.sort_order, item.created_at))

    def create_layer(self, map_id: UUID, **values: Any) -> Layer:
        with self._lock:
            layer = Layer(map_id=map_id, **values)
            self._layers[layer.id] = layer
            return layer

    def get_layer(self, layer_id: UUID) -> Layer | None:
        with self._lock:
            return self._layers.get(layer_id)

    def update_layer(
        self,
        layer_id: UUID,
        changes: Mapping[str, Any],
    ) -> Layer | None:
        with self._lock:
            layer = self._layers.get(layer_id)
            if layer is None:
                return None
            return self._apply_changes(layer, changes)

    def delete_layer(self, layer_id: UUID) -> bool:
        with self._lock:
            if layer_id not in self._layers:
                return False
            object_ids = [
                object_id
                for object_id, map_object in self._objects.items()
                if map_object.layer_id == layer_id
            ]
            for object_id in object_ids:
                del self._objects[object_id]
            del self._layers[layer_id]
            return True

    def list_objects(
        self,
        map_id: UUID | None = None,
        layer_id: UUID | None = None,
        visible: bool | None = None,
        audience: MapAudience | None = None,
    ) -> Sequence[MapObject]:
        with self._lock:
            objects = self._objects.values()
            if map_id is not None:
                objects = [item for item in objects if item.map_id == map_id]
            if layer_id is not None:
                objects = [item for item in objects if item.layer_id == layer_id]
            if visible is not None:
                objects = [item for item in objects if item.visible is visible]
            if audience is not None:
                objects = [
                    item
                    for item in objects
                    if _audience_value(item.audience) == _audience_value(audience)
                ]
            return sorted(objects, key=lambda item: item.created_at)

    def create_object(self, map_id: UUID, **values: Any) -> MapObject:
        with self._lock:
            map_object = MapObject(map_id=map_id, **values)
            self._objects[map_object.id] = map_object
            return map_object

    def get_object(self, object_id: UUID) -> MapObject | None:
        with self._lock:
            return self._objects.get(object_id)

    def update_object(
        self,
        object_id: UUID,
        changes: Mapping[str, Any],
    ) -> MapObject | None:
        with self._lock:
            map_object = self._objects.get(object_id)
            if map_object is None:
                return None
            return self._apply_changes(map_object, changes)

    def delete_object(self, object_id: UUID) -> bool:
        with self._lock:
            if object_id not in self._objects:
                return False
            del self._objects[object_id]
            return True

    def list_exports(self, map_id: UUID | None = None) -> Sequence[ExportJob]:
        with self._lock:
            exports = self._exports.values()
            if map_id is not None:
                exports = [item for item in exports if item.map_id == map_id]
            return sorted(exports, key=lambda item: item.requested_at)

    def create_export(self, map_id: UUID, **values: Any) -> ExportJob:
        with self._lock:
            export = ExportJob(map_id=map_id, **values)
            self._exports[export.id] = export
            return export

    def get_export(self, export_id: UUID) -> ExportJob | None:
        with self._lock:
            return self._exports.get(export_id)

    def _delete_map_cascade(self, map_id: UUID) -> None:
        layer_ids = [
            layer_id
            for layer_id, layer in self._layers.items()
            if layer.map_id == map_id
        ]
        object_ids = [
            object_id
            for object_id, map_object in self._objects.items()
            if map_object.map_id == map_id
        ]
        export_ids = [
            export_id
            for export_id, export in self._exports.items()
            if export.map_id == map_id
        ]

        for layer_id in layer_ids:
            del self._layers[layer_id]
        for object_id in object_ids:
            del self._objects[object_id]
        for export_id in export_ids:
            del self._exports[export_id]
        del self._maps[map_id]

    @staticmethod
    def _apply_changes(entity: Any, changes: Mapping[str, Any]) -> Any:
        for field_name, value in changes.items():
            setattr(entity, field_name, value)
        if hasattr(entity, "updated_at"):
            entity.updated_at = utc_now()
        return entity


def _audience_value(audience: MapAudience | str) -> str:
    if isinstance(audience, MapAudience):
        return audience.value
    return str(audience)
