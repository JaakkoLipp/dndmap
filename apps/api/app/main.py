from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router, health_router
from app.core.config import Settings, get_settings
from app.repositories.base import MapDataStore
from app.repositories.in_memory import InMemoryMapStore


def create_app(
    settings: Settings | None = None,
    store: MapDataStore | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = resolved_settings
        if store is not None:
            app.state.store = store
        elif (
            resolved_settings.persistence_backend == "postgres"
            and resolved_settings.database_url
        ):
            from app.db.engine import make_engine, make_session_factory
            from app.repositories.postgres import PostgresMapStore

            engine = make_engine(resolved_settings.database_url)
            factory = make_session_factory(engine)
            app.state.engine = engine
            app.state.session_factory = factory
            app.state.store = PostgresMapStore(factory)
        else:
            app.state.store = InMemoryMapStore()
        yield
        if hasattr(app.state, "engine"):
            await app.state.engine.dispose()

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.version,
        lifespan=lifespan,
    )

    if resolved_settings.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(health_router)
    app.include_router(api_router, prefix=resolved_settings.api_prefix)
    return app


app = create_app()
