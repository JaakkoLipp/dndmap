from collections.abc import Mapping, Sequence
from typing import Any, Protocol
from uuid import UUID

from app.domain.models import (
    Campaign,
    CampaignMap,
    ExportJob,
    Layer,
    MapAudience,
    MapObject,
)


class MapDataStore(Protocol):
    def list_campaigns(self) -> Sequence[Campaign]: ...

    def create_campaign(self, name: str, description: str | None = None) -> Campaign: ...

    def get_campaign(self, campaign_id: UUID) -> Campaign | None: ...

    def update_campaign(
        self,
        campaign_id: UUID,
        changes: Mapping[str, Any],
    ) -> Campaign | None: ...

    def delete_campaign(self, campaign_id: UUID) -> bool: ...

    def list_maps(self, campaign_id: UUID | None = None) -> Sequence[CampaignMap]: ...

    def create_map(self, campaign_id: UUID, **values: Any) -> CampaignMap: ...

    def get_map(self, map_id: UUID) -> CampaignMap | None: ...

    def update_map(
        self,
        map_id: UUID,
        changes: Mapping[str, Any],
    ) -> CampaignMap | None: ...

    def delete_map(self, map_id: UUID) -> bool: ...

    def list_layers(
        self,
        map_id: UUID | None = None,
        visible: bool | None = None,
        audience: MapAudience | None = None,
    ) -> Sequence[Layer]: ...

    def create_layer(self, map_id: UUID, **values: Any) -> Layer: ...

    def get_layer(self, layer_id: UUID) -> Layer | None: ...

    def update_layer(
        self,
        layer_id: UUID,
        changes: Mapping[str, Any],
    ) -> Layer | None: ...

    def delete_layer(self, layer_id: UUID) -> bool: ...

    def list_objects(
        self,
        map_id: UUID | None = None,
        layer_id: UUID | None = None,
        visible: bool | None = None,
        audience: MapAudience | None = None,
    ) -> Sequence[MapObject]: ...

    def create_object(self, map_id: UUID, **values: Any) -> MapObject: ...

    def get_object(self, object_id: UUID) -> MapObject | None: ...

    def update_object(
        self,
        object_id: UUID,
        changes: Mapping[str, Any],
    ) -> MapObject | None: ...

    def delete_object(self, object_id: UUID) -> bool: ...

    def list_exports(self, map_id: UUID | None = None) -> Sequence[ExportJob]: ...

    def create_export(self, map_id: UUID, **values: Any) -> ExportJob: ...

    def get_export(self, export_id: UUID) -> ExportJob | None: ...
