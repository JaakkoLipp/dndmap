from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.dependencies import StoreDependency, raise_not_found
from app.auth.dependencies import OptionalCurrentUser, get_campaign_member
from app.db import models as orm
from app.db.session import OptionalDbSession
from app.domain.models import utc_now
from app.domain.schemas import (
    CampaignCreate,
    CampaignMemberRead,
    CampaignRead,
    CampaignUpdate,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignRead])
async def list_campaigns(
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
) -> list:
    campaigns = await store.list_campaigns(user_id=user.id if user else None)
    if not campaigns:
        return campaigns

    if user is None:
        # Dev mode without auth: surface owner role so the UI shows pills.
        return [
            CampaignRead.model_validate(campaign).model_copy(
                update={"role": orm.CampaignRole.OWNER.value}
            )
            for campaign in campaigns
        ]

    if db is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not configured")
    campaign_ids = [campaign.id for campaign in campaigns]
    result = await db.execute(
        select(orm.CampaignMember.campaign_id, orm.CampaignMember.role).where(
            orm.CampaignMember.user_id == user.id,
            orm.CampaignMember.campaign_id.in_(campaign_ids),
        )
    )
    roles: dict[UUID, str] = {
        campaign_id: role.value for campaign_id, role in result.all()
    }
    return [
        CampaignRead.model_validate(campaign).model_copy(
            update={"role": roles.get(campaign.id)}
        )
        for campaign in campaigns
    ]


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
):
    campaign = await store.create_campaign(
        name=payload.name,
        description=payload.description,
        owner_id=user.id if user else None,
    )
    if user is not None and db is not None:
        db.add(
            orm.CampaignMember(
                campaign_id=campaign.id,
                user_id=user.id,
                role=orm.CampaignRole.OWNER,
            )
        )
        await db.commit()
    return campaign


@router.get("/{campaign_id}/me", response_model=CampaignMemberRead)
async def get_my_membership(
    campaign_id: UUID,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
):
    """Return the requesting user's role + join time for this campaign.

    In dev/memory mode (no auth) a synthetic owner membership is returned so
    the frontend can develop against the role-aware UI without auth wired.
    """
    if user is None:
        return CampaignMemberRead(
            campaign_id=campaign_id,
            user_id=UUID(int=0),
            role=orm.CampaignRole.OWNER.value,
            joined_at=utc_now(),
        )
    if db is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not configured")
    result = await db.execute(
        select(orm.CampaignMember).where(
            orm.CampaignMember.campaign_id == campaign_id,
            orm.CampaignMember.user_id == user.id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not a member")
    return member


@router.get("/{campaign_id}", response_model=CampaignRead)
async def read_campaign(
    campaign_id: UUID,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
):
    if user is not None:
        if db is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not configured")
        await get_campaign_member(campaign_id, user, db)
    campaign = await store.get_campaign(campaign_id)
    if campaign is None:
        raise_not_found("Campaign")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignRead)
async def update_campaign(
    campaign_id: UUID,
    payload: CampaignUpdate,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
):
    if user is not None:
        if db is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not configured")
        await get_campaign_member(campaign_id, user, db, minimum_role=orm.CampaignRole.DM)
    campaign = await store.update_campaign(
        campaign_id,
        payload.model_dump(exclude_unset=True),
    )
    if campaign is None:
        raise_not_found("Campaign")
    return campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: UUID,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
) -> Response:
    if user is not None:
        if db is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not configured")
        await get_campaign_member(campaign_id, user, db, minimum_role=orm.CampaignRole.OWNER)
    if not await store.delete_campaign(campaign_id):
        raise_not_found("Campaign")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
