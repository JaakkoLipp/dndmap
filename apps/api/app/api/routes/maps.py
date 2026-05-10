import re
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from uuid import UUID
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile, status
from starlette.concurrency import run_in_threadpool

from PIL import Image, UnidentifiedImageError

from app.api.dependencies import StorageDependency, StoreDependency, raise_not_found
from app.auth.dependencies import OptionalCurrentUser, get_campaign_member
from app.core.rate_limit import MutationRateLimit, UploadRateLimit
from app.db import models as orm
from app.db.session import OptionalDbSession
from app.domain.models import CampaignMap
from app.domain.schemas import MapCreate, MapRead, MapUpdate
from app.realtime import EventType, actor_from_user, publish_event, write_revision
from app.storage import ObjectStorage, StorageConfigurationError

router = APIRouter(tags=["maps"])


def _with_presigned_image_url(
    campaign_map: CampaignMap,
    storage: ObjectStorage,
) -> CampaignMap:
    if not campaign_map.image_object_key:
        return campaign_map

    image_url = storage.presigned_get_url(campaign_map.image_object_key)
    if not image_url:
        return campaign_map
    return replace(campaign_map, image_url=image_url)


def _safe_filename(filename: str | None) -> str:
    name = Path(filename or "map-image").name.strip() or "map-image"
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-") or "map-image"


def _read_image_size(body: bytes) -> tuple[int, int]:
    try:
        with Image.open(BytesIO(body)) as image:
            width, height = image.size
            image.verify()
            return width, height
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is not a valid image",
        ) from exc


@router.get("/campaigns/{campaign_id}/maps", response_model=list[MapRead])
async def list_maps(
    campaign_id: UUID,
    store: StoreDependency,
    storage: StorageDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
) -> list:
    if user is not None:
        assert db is not None
        await get_campaign_member(campaign_id, user, db)
    elif await store.get_campaign(campaign_id) is None:
        raise_not_found("Campaign")
    maps = await store.list_maps(campaign_id=campaign_id)
    return [_with_presigned_image_url(campaign_map, storage) for campaign_map in maps]


@router.post(
    "/campaigns/{campaign_id}/maps",
    response_model=MapRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_map(
    campaign_id: UUID,
    payload: MapCreate,
    store: StoreDependency,
    storage: StorageDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
    _limit: MutationRateLimit = None,
):
    if user is not None:
        assert db is not None
        await get_campaign_member(campaign_id, user, db, minimum_role=orm.CampaignRole.DM)
    elif await store.get_campaign(campaign_id) is None:
        raise_not_found("Campaign")
    campaign_map = await store.create_map(campaign_id=campaign_id, **payload.model_dump())
    return _with_presigned_image_url(campaign_map, storage)


@router.get("/maps/{map_id}", response_model=MapRead)
async def read_map(
    map_id: UUID,
    store: StoreDependency,
    storage: StorageDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
):
    campaign_map = await store.get_map(map_id)
    if campaign_map is None:
        raise_not_found("Map")
    if user is not None:
        assert db is not None
        await get_campaign_member(campaign_map.campaign_id, user, db)
    return _with_presigned_image_url(campaign_map, storage)


@router.patch("/maps/{map_id}", response_model=MapRead)
async def update_map(
    map_id: UUID,
    payload: MapUpdate,
    request: Request,
    store: StoreDependency,
    storage: StorageDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
    _limit: MutationRateLimit = None,
):
    campaign_map = await store.get_map(map_id)
    if campaign_map is None:
        raise_not_found("Map")
    if user is not None:
        assert db is not None
        await get_campaign_member(campaign_map.campaign_id, user, db, minimum_role=orm.CampaignRole.DM)
    changes = payload.model_dump(exclude_unset=True)
    updated = await store.update_map(map_id, changes)
    if updated is None:
        raise_not_found("Map")
    event_payload = {"fields": sorted(changes.keys())}
    await publish_event(
        request,
        map_id,
        EventType.MAP_UPDATED,
        actor=actor_from_user(user),
        payload=event_payload,
    )
    await write_revision(
        db,
        map_id=map_id,
        event_type=EventType.MAP_UPDATED,
        actor=user,
        summary=f"Updated map fields: {', '.join(event_payload['fields'])}"
        if event_payload["fields"]
        else "Updated map",
        payload=event_payload,
    )
    return _with_presigned_image_url(updated, storage)


@router.post("/maps/{map_id}/image", response_model=MapRead)
async def upload_map_image(
    map_id: UUID,
    request: Request,
    store: StoreDependency,
    storage: StorageDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
    _upload_limit: UploadRateLimit = None,
    file: UploadFile = File(...),
):
    campaign_map = await store.get_map(map_id)
    if campaign_map is None:
        raise_not_found("Map")
    if user is not None:
        assert db is not None
        await get_campaign_member(
            campaign_map.campaign_id,
            user,
            db,
            minimum_role=orm.CampaignRole.DM,
        )

    content_type = file.content_type or "application/octet-stream"
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Map upload must be an image",
        )

    body = await file.read()
    width, height = _read_image_size(body)
    filename = _safe_filename(file.filename)
    object_key = f"maps/{map_id}/{uuid4()}-{filename}"

    try:
        await run_in_threadpool(
            storage.put_object,
            key=object_key,
            body=body,
            content_type=content_type,
        )
    except StorageConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    updated = await store.update_map(
        map_id,
        {
            "width": width,
            "height": height,
            "image_object_key": object_key,
            "image_url": None,
            "image_name": filename,
            "image_content_type": content_type,
        },
    )
    if updated is None:
        raise_not_found("Map")
    event_payload = {"width": width, "height": height, "filename": filename}
    await publish_event(
        request,
        map_id,
        EventType.MAP_IMAGE_UPDATED,
        actor=actor_from_user(user),
        payload=event_payload,
    )
    await write_revision(
        db,
        map_id=map_id,
        event_type=EventType.MAP_IMAGE_UPDATED,
        actor=user,
        summary=f"Uploaded image \"{filename}\" ({width}×{height})",
        payload=event_payload,
    )
    return _with_presigned_image_url(updated, storage)


@router.delete("/maps/{map_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_map(
    map_id: UUID,
    request: Request,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
    _limit: MutationRateLimit = None,
) -> Response:
    campaign_map = await store.get_map(map_id)
    if campaign_map is None:
        raise_not_found("Map")
    if user is not None:
        assert db is not None
        await get_campaign_member(campaign_map.campaign_id, user, db, minimum_role=orm.CampaignRole.DM)
    if not await store.delete_map(map_id):
        raise_not_found("Map")
    await publish_event(
        request,
        map_id,
        EventType.MAP_DELETED,
        actor=actor_from_user(user),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
