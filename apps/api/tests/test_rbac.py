"""Tests for RBAC enforcement in API routes."""
from io import BytesIO
import types
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_campaign_member
from app.db import models as orm


class FakeStorage:
    def put_object(self, *, key: str, body: bytes, content_type: str) -> None:
        pass

    def presigned_get_url(self, key: str, *, expires_in: int = 3600) -> str | None:
        return f"https://assets.example.test/{key}?signed=1"


def _png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (4, 3), "#123456").save(buffer, format="PNG")
    return buffer.getvalue()


# --- Helpers ---

def _user(user_id=None):
    return types.SimpleNamespace(id=user_id or uuid.uuid4(), display_name="User")


def _member(campaign_id, user_id, role: orm.CampaignRole):
    return types.SimpleNamespace(campaign_id=campaign_id, user_id=user_id, role=role)


def _campaign_orm(campaign_id):
    c = orm.Campaign.__new__(orm.Campaign)
    # Use SQLAlchemy's instance state init trick
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.orm import InstanceState
    c.__dict__["_sa_instance_state"] = InstanceState(c, orm.Campaign.__mapper__)
    c.id = campaign_id
    return c


def _mock_db(member=None, campaign=None):
    db = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalar_one_or_none.return_value = member
    db.execute = AsyncMock(return_value=result)
    db.get = AsyncMock(return_value=campaign)
    return db


# --- get_campaign_member unit tests ---

async def test_viewer_passes_viewer_gate():
    campaign_id = uuid.uuid4()
    user = _user()
    db = _mock_db(member=_member(campaign_id, user.id, orm.CampaignRole.VIEWER))
    result = await get_campaign_member(campaign_id, user, db, minimum_role=orm.CampaignRole.VIEWER)
    assert result.role == orm.CampaignRole.VIEWER


async def test_player_passes_viewer_gate():
    campaign_id = uuid.uuid4()
    user = _user()
    db = _mock_db(member=_member(campaign_id, user.id, orm.CampaignRole.PLAYER))
    result = await get_campaign_member(campaign_id, user, db, minimum_role=orm.CampaignRole.VIEWER)
    assert result.role == orm.CampaignRole.PLAYER


async def test_viewer_blocked_by_dm_gate():
    campaign_id = uuid.uuid4()
    user = _user()
    db = _mock_db(member=_member(campaign_id, user.id, orm.CampaignRole.VIEWER))
    with pytest.raises(HTTPException) as exc:
        await get_campaign_member(campaign_id, user, db, minimum_role=orm.CampaignRole.DM)
    assert exc.value.status_code == 403


async def test_non_member_with_existing_campaign_gets_403():
    campaign_id = uuid.uuid4()
    user = _user()
    campaign = _campaign_orm(campaign_id)
    db = _mock_db(member=None, campaign=campaign)
    with pytest.raises(HTTPException) as exc:
        await get_campaign_member(campaign_id, user, db)
    assert exc.value.status_code == 403


async def test_non_member_missing_campaign_gets_404():
    campaign_id = uuid.uuid4()
    user = _user()
    db = _mock_db(member=None, campaign=None)
    with pytest.raises(HTTPException) as exc:
        await get_campaign_member(campaign_id, user, db)
    assert exc.value.status_code == 404


# --- Route-level RBAC tests ---

def test_non_member_cannot_read_campaign(auth_client, test_user, mock_db):
    created = auth_client.post("/api/v1/campaigns", json={"name": "Secret"})
    assert created.status_code == 201
    campaign_id = uuid.UUID(created.json()["id"])

    # campaign exists in mock DB but user has no membership
    mock_db.get.return_value = _campaign_orm(campaign_id)
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    assert auth_client.get(f"/api/v1/campaigns/{campaign_id}").status_code == 403


def test_viewer_can_read_campaign(auth_client, test_user, mock_db):
    created = auth_client.post("/api/v1/campaigns", json={"name": "Open"})
    assert created.status_code == 201
    campaign_id = uuid.UUID(created.json()["id"])

    mock_db.execute.return_value.scalar_one_or_none.return_value = _member(
        campaign_id, test_user.id, orm.CampaignRole.VIEWER
    )

    assert auth_client.get(f"/api/v1/campaigns/{campaign_id}").status_code == 200


def test_viewer_cannot_update_campaign(auth_client, test_user, mock_db):
    created = auth_client.post("/api/v1/campaigns", json={"name": "Frozen"})
    assert created.status_code == 201
    campaign_id = uuid.UUID(created.json()["id"])

    mock_db.execute.return_value.scalar_one_or_none.return_value = _member(
        campaign_id, test_user.id, orm.CampaignRole.VIEWER
    )

    assert (
        auth_client.patch(
            f"/api/v1/campaigns/{campaign_id}", json={"name": "Hacked"}
        ).status_code
        == 403
    )


def test_dm_can_update_campaign(auth_client, test_user, mock_db):
    created = auth_client.post("/api/v1/campaigns", json={"name": "DM Realm"})
    assert created.status_code == 201
    campaign_id = uuid.UUID(created.json()["id"])

    mock_db.execute.return_value.scalar_one_or_none.return_value = _member(
        campaign_id, test_user.id, orm.CampaignRole.DM
    )

    response = auth_client.patch(
        f"/api/v1/campaigns/{campaign_id}", json={"name": "Renamed"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_dm_cannot_delete_campaign(auth_client, test_user, mock_db):
    created = auth_client.post("/api/v1/campaigns", json={"name": "Sticky"})
    assert created.status_code == 201
    campaign_id = uuid.UUID(created.json()["id"])

    mock_db.execute.return_value.scalar_one_or_none.return_value = _member(
        campaign_id, test_user.id, orm.CampaignRole.DM
    )

    assert auth_client.delete(f"/api/v1/campaigns/{campaign_id}").status_code == 403


def test_owner_can_delete_campaign(auth_client, test_user, mock_db):
    created = auth_client.post("/api/v1/campaigns", json={"name": "Owned"})
    assert created.status_code == 201
    campaign_id = uuid.UUID(created.json()["id"])

    mock_db.execute.return_value.scalar_one_or_none.return_value = _member(
        campaign_id, test_user.id, orm.CampaignRole.OWNER
    )

    assert auth_client.delete(f"/api/v1/campaigns/{campaign_id}").status_code == 204


def test_create_campaign_inserts_owner_membership(auth_client, test_user, mock_db):
    response = auth_client.post("/api/v1/campaigns", json={"name": "New"})
    assert response.status_code == 201
    campaign_id = uuid.UUID(response.json()["id"])

    # Verify the route added an OWNER CampaignMember to the DB
    added_args = [call.args[0] for call in mock_db.add.call_args_list]
    members = [a for a in added_args if isinstance(a, orm.CampaignMember)]
    assert len(members) == 1
    assert members[0].role == orm.CampaignRole.OWNER
    assert members[0].user_id == test_user.id
    assert members[0].campaign_id == campaign_id


def test_viewer_cannot_create_map(auth_client, test_user, mock_db):
    campaign = auth_client.post("/api/v1/campaigns", json={"name": "C"}).json()
    campaign_id = uuid.UUID(campaign["id"])

    mock_db.execute.return_value.scalar_one_or_none.return_value = _member(
        campaign_id, test_user.id, orm.CampaignRole.VIEWER
    )

    assert (
        auth_client.post(
            f"/api/v1/campaigns/{campaign_id}/maps",
            json={"name": "Map", "width": 800, "height": 600},
        ).status_code
        == 403
    )


def test_dm_can_create_map(auth_client, test_user, mock_db):
    campaign = auth_client.post("/api/v1/campaigns", json={"name": "C"}).json()
    campaign_id = uuid.UUID(campaign["id"])

    mock_db.execute.return_value.scalar_one_or_none.return_value = _member(
        campaign_id, test_user.id, orm.CampaignRole.DM
    )

    assert (
        auth_client.post(
            f"/api/v1/campaigns/{campaign_id}/maps",
            json={"name": "Map", "width": 800, "height": 600},
        ).status_code
        == 201
    )


def test_viewer_cannot_upload_map_image(auth_client, test_user, mock_db):
    auth_client.app.state.storage = FakeStorage()
    campaign = auth_client.post("/api/v1/campaigns", json={"name": "C"}).json()
    campaign_id = uuid.UUID(campaign["id"])
    member = _member(campaign_id, test_user.id, orm.CampaignRole.DM)
    mock_db.execute.return_value.scalar_one_or_none.return_value = member

    campaign_map = auth_client.post(
        f"/api/v1/campaigns/{campaign_id}/maps",
        json={"name": "Map", "width": 800, "height": 600},
    ).json()

    member.role = orm.CampaignRole.VIEWER
    response = auth_client.post(
        f"/api/v1/maps/{campaign_map['id']}/image",
        files={"file": ("map.png", _png_bytes(), "image/png")},
    )

    assert response.status_code == 403


def test_player_cannot_upload_map_image(auth_client, test_user, mock_db):
    auth_client.app.state.storage = FakeStorage()
    campaign = auth_client.post("/api/v1/campaigns", json={"name": "C"}).json()
    campaign_id = uuid.UUID(campaign["id"])
    member = _member(campaign_id, test_user.id, orm.CampaignRole.DM)
    mock_db.execute.return_value.scalar_one_or_none.return_value = member

    campaign_map = auth_client.post(
        f"/api/v1/campaigns/{campaign_id}/maps",
        json={"name": "Map", "width": 800, "height": 600},
    ).json()

    member.role = orm.CampaignRole.PLAYER
    response = auth_client.post(
        f"/api/v1/maps/{campaign_map['id']}/image",
        files={"file": ("map.png", _png_bytes(), "image/png")},
    )

    assert response.status_code == 403


def test_player_can_create_object(auth_client, test_user, mock_db):
    # Setup as DM to create map and layer
    campaign = auth_client.post("/api/v1/campaigns", json={"name": "C"}).json()
    campaign_id = uuid.UUID(campaign["id"])
    member = _member(campaign_id, test_user.id, orm.CampaignRole.DM)
    mock_db.execute.return_value.scalar_one_or_none.return_value = member

    campaign_map = auth_client.post(
        f"/api/v1/campaigns/{campaign_id}/maps",
        json={"name": "Map", "width": 800, "height": 600},
    ).json()
    layer = auth_client.post(
        f"/api/v1/maps/{campaign_map['id']}/layers", json={"name": "Layer"}
    ).json()

    # Switch to PLAYER to create an object
    member.role = orm.CampaignRole.PLAYER
    response = auth_client.post(
        f"/api/v1/maps/{campaign_map['id']}/objects",
        json={
            "layer_id": layer["id"],
            "name": "Token",
            "kind": "marker",
            "x": 10, "y": 10, "width": 30, "height": 30,
        },
    )
    assert response.status_code == 201


def test_viewer_cannot_create_object(auth_client, test_user, mock_db):
    # Setup as DM to create map and layer
    campaign = auth_client.post("/api/v1/campaigns", json={"name": "C"}).json()
    campaign_id = uuid.UUID(campaign["id"])
    member = _member(campaign_id, test_user.id, orm.CampaignRole.DM)
    mock_db.execute.return_value.scalar_one_or_none.return_value = member

    campaign_map = auth_client.post(
        f"/api/v1/campaigns/{campaign_id}/maps",
        json={"name": "Map", "width": 800, "height": 600},
    ).json()
    layer = auth_client.post(
        f"/api/v1/maps/{campaign_map['id']}/layers", json={"name": "Layer"}
    ).json()

    # Switch to VIEWER to attempt object creation
    member.role = orm.CampaignRole.VIEWER
    response = auth_client.post(
        f"/api/v1/maps/{campaign_map['id']}/objects",
        json={
            "layer_id": layer["id"],
            "name": "Token",
            "kind": "marker",
            "x": 10, "y": 10, "width": 30, "height": 30,
        },
    )
    assert response.status_code == 403
