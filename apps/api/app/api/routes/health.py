from fastapi import APIRouter

from app.api.dependencies import SettingsDependency
from app.domain.schemas import HealthRead

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthRead)
async def read_health(settings: SettingsDependency) -> HealthRead:
    return HealthRead(
        status="ok",
        service=settings.app_name,
        version=settings.version,
        environment=settings.environment,
    )

