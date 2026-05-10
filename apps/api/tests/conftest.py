import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.repositories.in_memory import InMemoryMapStore


@pytest.fixture()
def client() -> TestClient:
    settings = Settings(
        app_name="Test D&D Map API",
        environment="test",
        api_prefix="/api/v1",
        enable_cors=False,
    )
    app = create_app(settings=settings, store=InMemoryMapStore())
    with TestClient(app) as test_client:
        yield test_client

