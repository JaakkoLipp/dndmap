from collections.abc import Mapping
from datetime import UTC
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import models as orm
from app.domain.models import (
    Campaign,
    CampaignMap,
    ExportJob,
    ExportFormat,
    ExportStatus,
    Layer,
    LayerKind,
    MapAudience,
    MapObject,
    MapObjectKind,
    utc_now,
)


def _to_campaign(row: orm.Campaign) -> Campaign:
    return Campaign(
        id=row.id,
        name=row.name,
        description=row.description,
        created_at=row.created_at.replace(tzinfo=UTC) if row.created_at.tzinfo is None else row.created_at,
        updated_at=row.updated_at.replace(tzinfo=UTC) if row.updated_at.tzinfo is None else row.updated_at,
    )


def _to_campaign_map(row: orm.CampaignMap) -> CampaignMap:
    return CampaignMap(
        id=row.id,
        campaign_id=row.campaign_id,
        name=row.name,
        width=row.width,
        height=row.height,
        grid_size=row.grid_size,
        background_color=row.background_color,
        image_object_key=row.image_object_key,
        image_url=row.image_url,
        image_name=row.image_name,
        image_content_type=row.image_content_type,
        created_at=row.created_at.replace(tzinfo=UTC) if row.created_at.tzinfo is None else row.created_at,
        updated_at=row.updated_at.replace(tzinfo=UTC) if row.updated_at.tzinfo is None else row.updated_at,
    )


def _to_layer(row: orm.MapLayer) -> Layer:
    return Layer(
        id=row.id,
        map_id=row.map_id,
        name=row.name,
        kind=LayerKind(row.kind),
        visible=row.visible,
        audience=MapAudience(row.audience),
        opacity=row.opacity,
        sort_order=row.sort_order,
        created_at=row.created_at.replace(tzinfo=UTC) if row.created_at.tzinfo is None else row.created_at,
        updated_at=row.updated_at.replace(tzinfo=UTC) if row.updated_at.tzinfo is None else row.updated_at,
    )


def _to_map_object(row: orm.MapObjectRow) -> MapObject:
    return MapObject(
        id=row.id,
        map_id=row.map_id,
        layer_id=row.layer_id,
        name=row.name,
        kind=MapObjectKind(row.kind),
        x=row.x,
        y=row.y,
        width=row.width,
        height=row.height,
        rotation=row.rotation,
        visible=row.visible,
        audience=MapAudience(row.audience),
        geometry=row.geometry,
        style=row.style,
        properties=row.properties or {},
        created_at=row.created_at.replace(tzinfo=UTC) if row.created_at.tzinfo is None else row.created_at,
        updated_at=row.updated_at.replace(tzinfo=UTC) if row.updated_at.tzinfo is None else row.updated_at,
    )


def _to_export_job(row: orm.MapExport) -> ExportJob:
    return ExportJob(
        id=row.id,
        map_id=row.map_id,
        format=ExportFormat(row.format),
        include_hidden_layers=row.include_hidden_layers,
        options=row.options or {},
        status=ExportStatus(row.status),
        error=row.error,
        download_url=row.download_url,
        requested_at=row.requested_at.replace(tzinfo=UTC) if row.requested_at.tzinfo is None else row.requested_at,
        completed_at=row.completed_at,
    )


class PostgresMapStore:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._factory = session_factory

    def _session(self) -> AsyncSession:
        return self._factory()

    # --- Campaigns ---

    async def list_campaigns(self, user_id: UUID | None = None) -> list[Campaign]:
        async with self._session() as session:
            if user_id is not None:
                stmt = (
                    select(orm.Campaign)
                    .join(
                        orm.CampaignMember,
                        orm.CampaignMember.campaign_id == orm.Campaign.id,
                    )
                    .where(orm.CampaignMember.user_id == user_id)
                    .order_by(orm.Campaign.created_at)
                )
            else:
                stmt = select(orm.Campaign).order_by(orm.Campaign.created_at)
            result = await session.execute(stmt)
            return [_to_campaign(row) for row in result.scalars()]

    async def create_campaign(
        self,
        name: str,
        description: str | None = None,
        owner_id: UUID | None = None,
    ) -> Campaign:
        async with self._session() as session:
            row = orm.Campaign(name=name, description=description, owner_id=owner_id)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _to_campaign(row)

    async def get_campaign(self, campaign_id: UUID) -> Campaign | None:
        async with self._session() as session:
            row = await session.get(orm.Campaign, campaign_id)
            return _to_campaign(row) if row else None

    async def update_campaign(
        self, campaign_id: UUID, changes: Mapping[str, Any]
    ) -> Campaign | None:
        async with self._session() as session:
            row = await session.get(orm.Campaign, campaign_id)
            if row is None:
                return None
            for key, value in changes.items():
                setattr(row, key, value)
            row.updated_at = utc_now()
            await session.commit()
            await session.refresh(row)
            return _to_campaign(row)

    async def delete_campaign(self, campaign_id: UUID) -> bool:
        async with self._session() as session:
            row = await session.get(orm.Campaign, campaign_id)
            if row is None:
                return False
            await session.delete(row)
            await session.commit()
            return True

    # --- Maps ---

    async def list_maps(self, campaign_id: UUID | None = None) -> list[CampaignMap]:
        async with self._session() as session:
            stmt = select(orm.CampaignMap).order_by(orm.CampaignMap.created_at)
            if campaign_id is not None:
                stmt = stmt.where(orm.CampaignMap.campaign_id == campaign_id)
            result = await session.execute(stmt)
            return [_to_campaign_map(row) for row in result.scalars()]

    async def create_map(self, campaign_id: UUID, **values: Any) -> CampaignMap:
        async with self._session() as session:
            row = orm.CampaignMap(campaign_id=campaign_id, **values)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _to_campaign_map(row)

    async def get_map(self, map_id: UUID) -> CampaignMap | None:
        async with self._session() as session:
            row = await session.get(orm.CampaignMap, map_id)
            return _to_campaign_map(row) if row else None

    async def update_map(self, map_id: UUID, changes: Mapping[str, Any]) -> CampaignMap | None:
        async with self._session() as session:
            row = await session.get(orm.CampaignMap, map_id)
            if row is None:
                return None
            for key, value in changes.items():
                setattr(row, key, value)
            row.updated_at = utc_now()
            await session.commit()
            await session.refresh(row)
            return _to_campaign_map(row)

    async def delete_map(self, map_id: UUID) -> bool:
        async with self._session() as session:
            row = await session.get(orm.CampaignMap, map_id)
            if row is None:
                return False
            await session.delete(row)
            await session.commit()
            return True

    # --- Layers ---

    async def list_layers(
        self,
        map_id: UUID | None = None,
        visible: bool | None = None,
        audience: MapAudience | None = None,
    ) -> list[Layer]:
        async with self._session() as session:
            stmt = select(orm.MapLayer).order_by(orm.MapLayer.sort_order, orm.MapLayer.created_at)
            if map_id is not None:
                stmt = stmt.where(orm.MapLayer.map_id == map_id)
            if visible is not None:
                stmt = stmt.where(orm.MapLayer.visible == visible)
            if audience is not None:
                stmt = stmt.where(orm.MapLayer.audience == audience.value)
            result = await session.execute(stmt)
            return [_to_layer(row) for row in result.scalars()]

    async def create_layer(self, map_id: UUID, **values: Any) -> Layer:
        async with self._session() as session:
            row = orm.MapLayer(map_id=map_id, **values)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _to_layer(row)

    async def get_layer(self, layer_id: UUID) -> Layer | None:
        async with self._session() as session:
            row = await session.get(orm.MapLayer, layer_id)
            return _to_layer(row) if row else None

    async def update_layer(
        self, layer_id: UUID, changes: Mapping[str, Any]
    ) -> Layer | None:
        async with self._session() as session:
            row = await session.get(orm.MapLayer, layer_id)
            if row is None:
                return None
            for key, value in changes.items():
                setattr(row, key, value)
            row.updated_at = utc_now()
            await session.commit()
            await session.refresh(row)
            return _to_layer(row)

    async def delete_layer(self, layer_id: UUID) -> bool:
        async with self._session() as session:
            row = await session.get(orm.MapLayer, layer_id)
            if row is None:
                return False
            await session.delete(row)
            await session.commit()
            return True

    # --- Objects ---

    async def list_objects(
        self,
        map_id: UUID | None = None,
        layer_id: UUID | None = None,
        visible: bool | None = None,
        audience: MapAudience | None = None,
    ) -> list[MapObject]:
        async with self._session() as session:
            stmt = select(orm.MapObjectRow).order_by(orm.MapObjectRow.created_at)
            if map_id is not None:
                stmt = stmt.where(orm.MapObjectRow.map_id == map_id)
            if layer_id is not None:
                stmt = stmt.where(orm.MapObjectRow.layer_id == layer_id)
            if visible is not None:
                stmt = stmt.where(orm.MapObjectRow.visible == visible)
            if audience is not None:
                stmt = stmt.where(orm.MapObjectRow.audience == audience.value)
            result = await session.execute(stmt)
            return [_to_map_object(row) for row in result.scalars()]

    async def create_object(self, map_id: UUID, **values: Any) -> MapObject:
        async with self._session() as session:
            row = orm.MapObjectRow(map_id=map_id, **values)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _to_map_object(row)

    async def get_object(self, object_id: UUID) -> MapObject | None:
        async with self._session() as session:
            row = await session.get(orm.MapObjectRow, object_id)
            return _to_map_object(row) if row else None

    async def update_object(
        self, object_id: UUID, changes: Mapping[str, Any]
    ) -> MapObject | None:
        async with self._session() as session:
            row = await session.get(orm.MapObjectRow, object_id)
            if row is None:
                return None
            for key, value in changes.items():
                setattr(row, key, value)
            row.updated_at = utc_now()
            await session.commit()
            await session.refresh(row)
            return _to_map_object(row)

    async def delete_object(self, object_id: UUID) -> bool:
        async with self._session() as session:
            row = await session.get(orm.MapObjectRow, object_id)
            if row is None:
                return False
            await session.delete(row)
            await session.commit()
            return True

    # --- Exports ---

    async def list_exports(self, map_id: UUID | None = None) -> list[ExportJob]:
        async with self._session() as session:
            stmt = select(orm.MapExport).order_by(orm.MapExport.requested_at)
            if map_id is not None:
                stmt = stmt.where(orm.MapExport.map_id == map_id)
            result = await session.execute(stmt)
            return [_to_export_job(row) for row in result.scalars()]

    async def create_export(self, map_id: UUID, **values: Any) -> ExportJob:
        async with self._session() as session:
            row = orm.MapExport(map_id=map_id, **values)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _to_export_job(row)

    async def get_export(self, export_id: UUID) -> ExportJob | None:
        async with self._session() as session:
            row = await session.get(orm.MapExport, export_id)
            return _to_export_job(row) if row else None
