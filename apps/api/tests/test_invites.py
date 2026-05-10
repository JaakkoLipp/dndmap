"""Tests for invite creation and acceptance routes."""
import types
import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db import models as orm
from app.domain.models import utc_now


# --- Helpers ---

def _member(campaign_id, user_id, role: orm.CampaignRole):
    return types.SimpleNamespace(campaign_id=campaign_id, user_id=user_id, role=role)


def _invite(campaign_id, creator_id, *, code="testcode",
            role=orm.CampaignRole.PLAYER, max_uses=None,
            use_count=0, expires_at=None):
    return types.SimpleNamespace(
        id=uuid.uuid4(),
        campaign_id=campaign_id,
        created_by_user_id=creator_id,
        code=code,
        role=role,
        max_uses=max_uses,
        use_count=use_count,
        expires_at=expires_at,
        created_at=utc_now(),
    )


def _result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


# --- create_invite ---

def test_dm_can_create_invite(auth_client, test_user, mock_db):
    campaign_id = uuid.uuid4()
    mock_db.execute.return_value.scalar_one_or_none.return_value = _member(
        campaign_id, test_user.id, orm.CampaignRole.DM
    )

    async def _refresh(obj):
        obj.id = uuid.uuid4()
        obj.created_at = utc_now()
        obj.use_count = 0

    mock_db.refresh = AsyncMock(side_effect=_refresh)

    response = auth_client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": "player"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["campaign_id"] == str(campaign_id)
    assert data["role"] == "player"
    assert data["use_count"] == 0
    assert "code" in data
    assert data["max_uses"] is None


def test_owner_can_create_invite_with_options(auth_client, test_user, mock_db):
    campaign_id = uuid.uuid4()
    mock_db.execute.return_value.scalar_one_or_none.return_value = _member(
        campaign_id, test_user.id, orm.CampaignRole.OWNER
    )

    async def _refresh(obj):
        obj.id = uuid.uuid4()
        obj.created_at = utc_now()
        obj.use_count = 0

    mock_db.refresh = AsyncMock(side_effect=_refresh)

    response = auth_client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": "viewer", "max_uses": 10, "expires_in_hours": 48},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "viewer"
    assert data["max_uses"] == 10
    assert data["expires_at"] is not None


def test_viewer_cannot_create_invite(auth_client, test_user, mock_db):
    campaign_id = uuid.uuid4()
    mock_db.execute.return_value.scalar_one_or_none.return_value = _member(
        campaign_id, test_user.id, orm.CampaignRole.VIEWER
    )
    assert (
        auth_client.post(
            f"/api/v1/campaigns/{campaign_id}/invites",
            json={"role": "player"},
        ).status_code
        == 403
    )


def test_player_cannot_create_invite(auth_client, test_user, mock_db):
    campaign_id = uuid.uuid4()
    mock_db.execute.return_value.scalar_one_or_none.return_value = _member(
        campaign_id, test_user.id, orm.CampaignRole.PLAYER
    )
    assert (
        auth_client.post(
            f"/api/v1/campaigns/{campaign_id}/invites",
            json={"role": "player"},
        ).status_code
        == 403
    )


def test_create_invite_adds_to_db(auth_client, test_user, mock_db):
    campaign_id = uuid.uuid4()
    mock_db.execute.return_value.scalar_one_or_none.return_value = _member(
        campaign_id, test_user.id, orm.CampaignRole.DM
    )

    async def _refresh(obj):
        obj.id = uuid.uuid4()
        obj.created_at = utc_now()
        obj.use_count = 0

    mock_db.refresh = AsyncMock(side_effect=_refresh)

    auth_client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": "player"},
    )

    added_args = [c.args[0] for c in mock_db.add.call_args_list]
    invites = [a for a in added_args if isinstance(a, orm.CampaignInvite)]
    assert len(invites) == 1
    assert invites[0].campaign_id == campaign_id
    assert invites[0].created_by_user_id == test_user.id
    assert invites[0].role == orm.CampaignRole.PLAYER
    mock_db.commit.assert_awaited()


# --- accept_invite ---

def test_accept_valid_invite(auth_client, test_user, mock_db):
    campaign_id = uuid.uuid4()
    invite = _invite(campaign_id, uuid.uuid4(), code="validcode")

    mock_db.execute = AsyncMock(side_effect=[
        _result(invite),       # invite lookup
        _result(None),         # no existing membership
    ])

    async def _refresh(obj):
        obj.joined_at = utc_now()

    mock_db.refresh = AsyncMock(side_effect=_refresh)

    response = auth_client.post("/api/v1/invites/validcode/accept")
    assert response.status_code == 201
    data = response.json()
    assert data["campaign_id"] == str(campaign_id)
    assert data["user_id"] == str(test_user.id)
    assert data["role"] == "player"


def test_accept_nonexistent_invite(auth_client, test_user, mock_db):
    mock_db.execute = AsyncMock(return_value=_result(None))
    assert auth_client.post("/api/v1/invites/nosuchcode/accept").status_code == 404


def test_accept_expired_invite(auth_client, test_user, mock_db):
    campaign_id = uuid.uuid4()
    invite = _invite(
        campaign_id, uuid.uuid4(),
        code="expiredcode",
        expires_at=utc_now() - timedelta(hours=1),
    )
    mock_db.execute = AsyncMock(return_value=_result(invite))
    assert auth_client.post("/api/v1/invites/expiredcode/accept").status_code == 410


def test_accept_maxed_out_invite(auth_client, test_user, mock_db):
    campaign_id = uuid.uuid4()
    invite = _invite(campaign_id, uuid.uuid4(), code="maxcode", max_uses=5, use_count=5)
    mock_db.execute = AsyncMock(return_value=_result(invite))
    assert auth_client.post("/api/v1/invites/maxcode/accept").status_code == 409


def test_accept_invite_at_limit_minus_one_succeeds(auth_client, test_user, mock_db):
    campaign_id = uuid.uuid4()
    invite = _invite(campaign_id, uuid.uuid4(), code="almostcode", max_uses=5, use_count=4)

    mock_db.execute = AsyncMock(side_effect=[
        _result(invite),
        _result(None),
    ])

    async def _refresh(obj):
        obj.joined_at = utc_now()

    mock_db.refresh = AsyncMock(side_effect=_refresh)

    assert auth_client.post("/api/v1/invites/almostcode/accept").status_code == 201


def test_accept_duplicate_membership(auth_client, test_user, mock_db):
    campaign_id = uuid.uuid4()
    invite = _invite(campaign_id, uuid.uuid4(), code="dupcode")
    existing = _member(campaign_id, test_user.id, orm.CampaignRole.PLAYER)

    mock_db.execute = AsyncMock(side_effect=[
        _result(invite),
        _result(existing),  # already a member
    ])

    assert auth_client.post("/api/v1/invites/dupcode/accept").status_code == 409


def test_accept_increments_use_count(auth_client, test_user, mock_db):
    campaign_id = uuid.uuid4()
    invite = _invite(campaign_id, uuid.uuid4(), code="countcode", max_uses=3, use_count=1)

    mock_db.execute = AsyncMock(side_effect=[
        _result(invite),
        _result(None),
    ])

    async def _refresh(obj):
        obj.joined_at = utc_now()

    mock_db.refresh = AsyncMock(side_effect=_refresh)

    auth_client.post("/api/v1/invites/countcode/accept")

    assert invite.use_count == 2
    mock_db.commit.assert_awaited()


def test_accept_adds_member_to_db(auth_client, test_user, mock_db):
    campaign_id = uuid.uuid4()
    invite = _invite(campaign_id, uuid.uuid4(), code="membercode",
                     role=orm.CampaignRole.VIEWER)

    mock_db.execute = AsyncMock(side_effect=[
        _result(invite),
        _result(None),
    ])

    async def _refresh(obj):
        obj.joined_at = utc_now()

    mock_db.refresh = AsyncMock(side_effect=_refresh)

    auth_client.post("/api/v1/invites/membercode/accept")

    added_args = [c.args[0] for c in mock_db.add.call_args_list]
    members = [a for a in added_args if isinstance(a, orm.CampaignMember)]
    assert len(members) == 1
    assert members[0].campaign_id == campaign_id
    assert members[0].user_id == test_user.id
    assert members[0].role == orm.CampaignRole.VIEWER
