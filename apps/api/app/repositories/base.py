from collections.abc import Mapping
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
    async def list_campaigns(self, user_id: UUID | None = None) -> list[Campaign]: ...

    async def create_campaign(
        self,
        name: str,
        description: str | None = None,
        owner_id: UUID | None = None,
    ) -> Campaign: ...

    async def get_campaign(self, campaign_id: UUID) -> Campaign | None: ...

    async def update_campaign(
        self,
        campaign_id: UUID,
        changes: Mapping[str, Any],
    ) -> Campaign | None: ...

    async def delete_campaign(self, campaign_id: UUID) -> bool: ...

    async def list_maps(self, campaign_id: UUID | None = None) -> list[CampaignMap]: ...

    async def create_map(self, campaign_id: UUID, **values: Any) -> CampaignMap: ...

    async def get_map(self, map_id: UUID) -> CampaignMap | None: ...

    async def update_map(
        self,
        map_id: UUID,
        changes: Mapping[str, Any],
    ) -> CampaignMap | None: ...

    async def delete_map(self, map_id: UUID) -> bool: ...

    async def list_layers(
        self,
        map_id: UUID | None = None,
        visible: bool | None = None,
        audience: MapAudience | None = None,
    ) -> list[Layer]: ...

    async def create_layer(self, map_id: UUID, **values: Any) -> Layer: ...

    async def get_layer(self, layer_id: UUID) -> Layer | None: ...

    async def update_layer(
        self,
        layer_id: UUID,
        changes: Mapping[str, Any],
    ) -> Layer | None: ...

    async def delete_layer(self, layer_id: UUID) -> bool: ...

    async def list_objects(
        self,
        map_id: UUID | None = None,
        layer_id: UUID | None = None,
        visible: bool | None = None,
        audience: MapAudience | None = None,
    ) -> list[MapObject]: ...

    async def create_object(self, map_id: UUID, **values: Any) -> MapObject: ...

    async def get_object(self, object_id: UUID) -> MapObject | None: ...

    async def update_object(
        self,
        object_id: UUID,
        changes: Mapping[str, Any],
    ) -> MapObject | None: ...

    async def delete_object(self, object_id: UUID) -> bool: ...

    async def list_exports(self, map_id: UUID | None = None) -> list[ExportJob]: ...

    async def create_export(self, map_id: UUID, **values: Any) -> ExportJob: ...

    async def get_export(self, export_id: UUID) -> ExportJob | None: ...
