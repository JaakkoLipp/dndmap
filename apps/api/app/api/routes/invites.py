import secrets
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.auth.dependencies import CurrentUser, get_campaign_member
from app.db import models as orm
from app.db.session import OptionalDbSession
from app.domain.models import utc_now
from app.domain.schemas import CampaignMemberRead, InviteCreate, InviteRead

router = APIRouter(tags=["invites"])


def _require_db(db) -> None:
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Invites require a database (PERSISTENCE_BACKEND=postgres + DATABASE_URL).",
        )


@router.post(
    "/campaigns/{campaign_id}/invites",
    response_model=InviteRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_invite(
    campaign_id: UUID,
    payload: InviteCreate,
    user: CurrentUser,
    db: OptionalDbSession,
) -> orm.CampaignInvite:
    _require_db(db)
    await get_campaign_member(campaign_id, user, db, minimum_role=orm.CampaignRole.DM)

    expires_at = None
    if payload.expires_in_hours is not None:
        expires_at = utc_now() + timedelta(hours=payload.expires_in_hours)

    invite = orm.CampaignInvite(
        campaign_id=campaign_id,
        created_by_user_id=user.id,
        code=secrets.token_urlsafe(32),
        role=orm.CampaignRole(payload.role),
        max_uses=payload.max_uses,
        expires_at=expires_at,
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return invite


@router.post(
    "/invites/{code}/accept",
    response_model=CampaignMemberRead,
    status_code=status.HTTP_201_CREATED,
)
async def accept_invite(
    code: str,
    user: CurrentUser,
    db: OptionalDbSession,
) -> orm.CampaignMember:
    _require_db(db)
    result = await db.execute(
        select(orm.CampaignInvite).where(orm.CampaignInvite.code == code)
    )
    invite = result.scalar_one_or_none()
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")

    if invite.expires_at is not None and invite.expires_at < utc_now():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invite has expired")

    if invite.max_uses is not None and invite.use_count >= invite.max_uses:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invite has reached max uses")

    existing = await db.execute(
        select(orm.CampaignMember).where(
            orm.CampaignMember.campaign_id == invite.campaign_id,
            orm.CampaignMember.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already a member of this campaign")

    member = orm.CampaignMember(
        campaign_id=invite.campaign_id,
        user_id=user.id,
        role=invite.role,
    )
    db.add(member)

    invite.use_count += 1

    await db.commit()
    await db.refresh(member)
    return member
