# AGENTS.md — Multi-Agent Collaboration Guide

This document defines module ownership and interface contracts so multiple AI agents can contribute to the repo without stepping on each other.

## Module Ownership

| Directory / File | Responsible Track | Description |
|---|---|---|
| `apps/api/app/db/` | Backend-Persistence | SQLAlchemy ORM models, engine factory, session dependency |
| `apps/api/app/repositories/` | Backend-Persistence | `MapDataStore` Protocol, `InMemoryMapStore`, `PostgresMapStore` |
| `apps/api/app/auth/` | Backend-Auth | JWT helpers, cookie helpers, OAuth state, provider adapters, dependencies |
| `apps/api/app/api/routes/auth.py` | Backend-Auth | OAuth login/callback, logout, `/auth/me` |
| `apps/api/app/api/routes/invites.py` | Backend-Auth | Invite creation and acceptance |
| `apps/api/app/api/routes/` (others) | Backend-Persistence + Backend-Auth | Campaigns/maps/layers/objects/exports — persistence then RBAC |
| `apps/api/alembic/` | Backend-Persistence | Migrations — **never edit manually**; use `alembic revision` |
| `apps/api/app/cli/` | Backend-Persistence | `dndmap-db` CLI entry point |
| `apps/web/components/map/` | Frontend-Konva | Konva-based canvas components |
| `apps/web/hooks/` | Frontend-Konva | `useMapState`, `useMapViewport` |
| `apps/web/components/providers/` | Frontend-Auth | `QueryProvider`, `AuthProvider` |
| `apps/web/app/login/` | Frontend-Auth | Login page |
| `apps/web/app/campaigns/` | Frontend-Auth | Campaign list and detail pages |
| `apps/web/app/invite/` | Frontend-Auth | Invite acceptance page |
| `apps/web/lib/api.ts` | Frontend-Auth | Unified API client (shared by all frontend tracks) |

## Interface Contracts Between Tracks

### Backend contracts
- **MapDataStore Protocol** (`app/repositories/base.py`) — all methods are `async def`. Both `InMemoryMapStore` and `PostgresMapStore` must satisfy this protocol. Tests use `InMemoryMapStore` by default.
- **DB session** (`app/db/session.py`) — routes that need direct DB access (auth, invites) inject `DbSession`. Routes that use `MapDataStore` inject `StoreDependency`. Do not mix the two for the same operation.
- **JWT payload** — always `{"sub": str(user_id), "iat": ..., "exp": ...}`. Never embed roles or campaign lists in the token; query `campaign_members` per request.
- **Auth guard** — `CurrentUser` dependency (`app/auth/dependencies.py`) requires `AUTH_ENABLED=true` and a valid `access_token` cookie. When `AUTH_ENABLED=false` the routes that use `StoreDependency` are still accessible without auth (useful for local dev without Postgres).

### Frontend contracts
- All API calls go through `lib/api.ts` with `credentials: "include"`. Never call `fetch` directly in components.
- TanStack Query key conventions: `["campaigns"]`, `["campaigns", id]`, `["campaigns", id, "maps"]`, `["maps", mapId, "layers"]`, `["maps", mapId, "objects", filters]`, `["auth", "me"]`.
- Auth state is read via `useAuth()` from `AuthProvider`. Components never read cookies or JWT directly.
- Konva components must use `"use client"` directive. `MapEditor` must be loaded via `dynamic(..., { ssr: false })` at the page level.

## Coordination Rules

1. **New database migrations**: coordinate with Backend-Persistence before adding `alembic revision`. Never add two migrations with the same `down_revision`. The migration chain must stay linear.
2. **`app/domain/schemas.py`**: shared by all backend tracks. Add new schemas; do not remove or rename existing fields without checking all routes that reference them.
3. **`lib/api.ts`**: shared by Frontend-Konva and Frontend-Auth. Add new typed methods; do not restructure the `apiFetch` core.
4. **`docker-compose.yml`**: coordinate env var additions with `.env.example`.

## API Reference

FastAPI auto-generates OpenAPI docs at `http://localhost:8000/docs` (or `/api/v1/docs` through nginx at `http://localhost:8080/api/v1/docs`). This is the authoritative API contract. Do not maintain a separate API spec file.

## Running Tests

```bash
cd apps/api
pytest                           # in-memory store, all tests
pytest -k "test_auth"            # auth-specific
POSTGRES_TEST_URL=postgresql+asyncpg://... pytest -m integration
```
