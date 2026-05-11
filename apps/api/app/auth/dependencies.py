from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookie import get_token_from_cookie
from app.auth.jwt import decode_token
from app.core.config import Settings
from app.db import models as orm
from app.db.session import DbSession, OptionalDbSession


async def _get_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_current_user(
    request: Request,
    db: OptionalDbSession,
) -> orm.User:
    settings: Settings = request.app.state.settings
    if not settings.auth_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth not enabled")
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured (set PERSISTENCE_BACKEND=postgres + DATABASE_URL)",
        )
    token = get_token_from_cookie(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = decode_token(token, settings)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = await db.get(orm.User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_optional_current_user(
    request: Request,
    db: OptionalDbSession,
) -> orm.User | None:
    """Returns the current user when AUTH_ENABLED=true, None otherwise.

    Used to gate RBAC: when None, all operations are permitted (dev/memory mode).
    When set, role checks are enforced using the database.
    """
    settings: Settings = request.app.state.settings
    if not settings.auth_enabled:
        return None
    token = get_token_from_cookie(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = decode_token(token, settings)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not configured")
    user = await db.get(orm.User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


CurrentUser = Annotated[orm.User, Depends(get_current_user)]
OptionalCurrentUser = Annotated[orm.User | None, Depends(get_optional_current_user)]

_ROLE_ORDER = [
    orm.CampaignRole.VIEWER,
    orm.CampaignRole.PLAYER,
    orm.CampaignRole.DM,
    orm.CampaignRole.OWNER,
]


async def get_campaign_member(
    campaign_id: UUID,
    user: orm.User,
    db: AsyncSession,
    minimum_role: orm.CampaignRole = orm.CampaignRole.VIEWER,
) -> orm.CampaignMember:
    """Resolve membership row and enforce minimum role, raising 403/404 as needed."""
    result = await db.execute(
        select(orm.CampaignMember).where(
            orm.CampaignMember.campaign_id == campaign_id,
            orm.CampaignMember.user_id == user.id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        campaign = await db.get(orm.Campaign, campaign_id)
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this campaign")
    if _ROLE_ORDER.index(member.role) < _ROLE_ORDER.index(minimum_role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return member
