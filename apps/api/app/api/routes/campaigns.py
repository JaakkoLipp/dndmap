from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.dependencies import StoreDependency, raise_not_found
from app.auth.dependencies import OptionalCurrentUser, get_campaign_member
from app.db import models as orm
from app.db.session import OptionalDbSession
from app.domain.schemas import CampaignCreate, CampaignRead, CampaignUpdate

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignRead])
async def list_campaigns(
    store: StoreDependency,
    user: OptionalCurrentUser,
) -> list:
    return await store.list_campaigns(user_id=user.id if user else None)


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


@router.get("/{campaign_id}", response_model=CampaignRead)
async def read_campaign(
    campaign_id: UUID,
    store: StoreDependency,
    user: OptionalCurrentUser,
    db: OptionalDbSession,
):
    if user is not None:
        assert db is not None
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
        assert db is not None
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
        assert db is not None
        await get_campaign_member(campaign_id, user, db, minimum_role=orm.CampaignRole.OWNER)
    if not await store.delete_campaign(campaign_id):
        raise_not_found("Campaign")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
