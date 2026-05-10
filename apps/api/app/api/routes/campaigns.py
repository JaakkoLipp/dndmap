from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.dependencies import StoreDependency, raise_not_found
from app.domain.schemas import CampaignCreate, CampaignRead, CampaignUpdate

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignRead])
def list_campaigns(store: StoreDependency) -> list:
    return list(store.list_campaigns())


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
def create_campaign(payload: CampaignCreate, store: StoreDependency):
    return store.create_campaign(
        name=payload.name,
        description=payload.description,
    )


@router.get("/{campaign_id}", response_model=CampaignRead)
def read_campaign(campaign_id: UUID, store: StoreDependency):
    campaign = store.get_campaign(campaign_id)
    if campaign is None:
        raise_not_found("Campaign")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignRead)
def update_campaign(
    campaign_id: UUID,
    payload: CampaignUpdate,
    store: StoreDependency,
):
    campaign = store.update_campaign(
        campaign_id,
        payload.model_dump(exclude_unset=True),
    )
    if campaign is None:
        raise_not_found("Campaign")
    return campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(campaign_id: UUID, store: StoreDependency) -> Response:
    if not store.delete_campaign(campaign_id):
        raise_not_found("Campaign")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

