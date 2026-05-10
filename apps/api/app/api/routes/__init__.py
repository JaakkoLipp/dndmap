from fastapi import APIRouter

from app.api.routes import campaigns, exports, health, layers, maps, objects, realtime

health_router = APIRouter()
health_router.include_router(health.router)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(campaigns.router)
api_router.include_router(maps.router)
api_router.include_router(layers.router)
api_router.include_router(objects.router)
api_router.include_router(exports.router)
api_router.include_router(realtime.router)

