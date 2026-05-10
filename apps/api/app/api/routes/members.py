"""Campaign membership management.

- ``GET /campaigns/{campaign_id}/members`` — anyone in the campaign can see
  the roster, joined to the user record so the UI can show names/avatars.
- ``PATCH /campaigns/{campaign_id}/members/{user_id}`` — owners change
  roles. Demoting the last remaining owner is rejected (the campaign must
  always have at least one owner).
- ``DELETE /campaigns/{campaign_id}/members/{user_id}`` — owners remove
  any member; non-owners may remove themselves only. The last owner cannot
  be removed.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.auth.dependencies import OptionalCurrentUser, get_campaign_member
from app.core.rate_limit import MutationRateLimit
from app.db import models as orm
from app.db.session import OptionalDbSession
from app.domain.schemas import CampaignMemberDetail, CampaignMemberUpdate

router = APIRouter(tags=["members"])


_ALLOWED_ROLES = {
    orm.CampaignRole.OWNER,
    orm.CampaignRole.DM,
    orm.CampaignRole.PLAYER,
    orm.CampaignRole.VIEWER,
}


async def _lock_owners(db, campaign_id: UUID) -> list[orm.CampaignMember]:
    """Acquire row-level locks on every owner row for ``campaign_id``.

    Used by mutations that need to enforce "at least one owner" without
    races: while one transaction holds these locks, concurrent
    demotions / removals serialize behind it. Rows are released when the
    enclosing transaction commits or rolls back.
    """
    result = await db.execute(
        select(orm.CampaignMember)
        .where(
            orm.CampaignMember.campaign_id == campaign_id,
            orm.CampaignMember.role == orm.CampaignRole.OWNER,
        )
        .with_for_update()
    )
    return list(result.scalars().all())


@router.get(
    "/campaigns/{campaign_id}/members",
    response_model=list[CampaignMemberDetail],
)
async def list_members(
    campaign_id: UUID,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
) -> list:
    if user is None or db is None:
        # Dev/in-memory mode has no campaign_members table; return empty
        # so the UI renders cleanly without auth wired up.
        return []
    await get_campaign_member(campaign_id, user, db)
    result = await db.execute(
        select(orm.CampaignMember, orm.User)
        .join(orm.User, orm.User.id == orm.CampaignMember.user_id)
        .where(orm.CampaignMember.campaign_id == campaign_id)
        .order_by(orm.CampaignMember.joined_at)
    )
    return [
        CampaignMemberDetail(
            campaign_id=member.campaign_id,
            user_id=member.user_id,
            role=member.role.value,
            joined_at=member.joined_at,
            display_name=user_row.display_name,
            avatar_url=user_row.avatar_url,
        )
        for member, user_row in result.all()
    ]


@router.patch(
    "/campaigns/{campaign_id}/members/{user_id}",
    response_model=CampaignMemberDetail,
)
async def update_member_role(
    campaign_id: UUID,
    user_id: UUID,
    payload: CampaignMemberUpdate,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
    _limit: MutationRateLimit = None,
):
    if user is None or db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Member management requires authentication",
        )
    await get_campaign_member(campaign_id, user, db, minimum_role=orm.CampaignRole.OWNER)

    new_role = orm.CampaignRole(payload.role)
    if new_role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role")

    # Lock owner rows before reading the count so the check + write happen
    # in a single serialized transaction. Concurrent demotions are made to
    # wait until this transaction completes.
    owners = await _lock_owners(db, campaign_id)

    member = await db.get(orm.CampaignMember, (campaign_id, user_id))
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if (
        member.role == orm.CampaignRole.OWNER
        and new_role != orm.CampaignRole.OWNER
        and len(owners) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot demote the last owner",
        )

    member.role = new_role
    await db.commit()
    await db.refresh(member)

    user_row = await db.get(orm.User, user_id)
    assert user_row is not None
    return CampaignMemberDetail(
        campaign_id=member.campaign_id,
        user_id=member.user_id,
        role=member.role.value,
        joined_at=member.joined_at,
        display_name=user_row.display_name,
        avatar_url=user_row.avatar_url,
    )


@router.delete(
    "/campaigns/{campaign_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    campaign_id: UUID,
    user_id: UUID,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
    _limit: MutationRateLimit = None,
) -> Response:
    if user is None or db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Member management requires authentication",
        )

    is_self = user_id == user.id
    if is_self:
        # Members may leave a campaign they belong to.
        await get_campaign_member(campaign_id, user, db)
    else:
        # Only owners can remove other members.
        await get_campaign_member(
            campaign_id, user, db, minimum_role=orm.CampaignRole.OWNER
        )

    # Same locking pattern as the role-change path: serialize concurrent
    # removals so the last-owner invariant cannot be raced past.
    owners = await _lock_owners(db, campaign_id)

    member = await db.get(orm.CampaignMember, (campaign_id, user_id))
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if member.role == orm.CampaignRole.OWNER and len(owners) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot remove the last owner",
        )

    await db.delete(member)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
