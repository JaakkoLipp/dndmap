from fastapi import APIRouter

from app.api.routes import (
    auth,
    campaigns,
    exports,
    health,
    invites,
    layers,
    maps,
    members,
    objects,
    realtime,
    revisions,
)

health_router = APIRouter()
health_router.include_router(health.router)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(campaigns.router)
api_router.include_router(maps.router)
api_router.include_router(layers.router)
api_router.include_router(objects.router)
api_router.include_router(exports.router)
api_router.include_router(invites.router)
api_router.include_router(members.router)
api_router.include_router(realtime.router)
api_router.include_router(revisions.router)
