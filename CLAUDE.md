# CLAUDE.md — Project Architecture Reference

## Overview

Self-hosted D&D campaign map app. Monorepo with:
- `apps/api/` — FastAPI Python 3.12 backend
- `apps/web/` — Next.js 15 / React 19 TypeScript frontend
- `infra/` — Docker Compose, nginx config, Dockerfiles

Milestone 2 (Postgres persistence), Milestone 3 map image upload, and Milestone 4 backend (OAuth + RBAC + invites) are **complete**. The frontend hosted shell for auth, campaigns, invites, and persisted editor routes is started; the remaining large frontend refactor is Track C (Konva canvas rewrite). See `TODO.md` for the full checklist and `docs/roadmap.md` for milestone definitions.

## Backend (`apps/api/`)

### Key conventions
- All repository methods are `async def`. Routes use `async def` with `await`.
- Two injection patterns:
  - `StoreDependency` — injects `MapDataStore` (in-memory or postgres depending on `PERSISTENCE_BACKEND`)
  - `DbSession` — injects `AsyncSession` for routes that need direct ORM access (auth, invites)
- JWT: HS256, `{"sub": user_id}` only. Roles queried from `campaign_members` per request — never embedded in token.
- Auth cookie: `access_token`, httpOnly, SameSite=lax, Secure in production only.
- OAuth state: signed with `itsdangerous.URLSafeTimedSerializer` using `SESSION_SECRET`.

### Environment variables (key ones)
| Variable | Default | Purpose |
|---|---|---|
| `PERSISTENCE_BACKEND` | `memory` | `memory` or `postgres` |
| `DATABASE_URL` | — | `postgresql+asyncpg://...` |
| `AUTH_ENABLED` | `false` | Enable JWT auth guard |
| `JWT_SECRET` | — | HS256 signing key |
| `SESSION_SECRET` | — | OAuth state HMAC key |
| `OAUTH_REDIRECT_BASE_URL` | `http://localhost:8080/api/v1/auth` | Base for OAuth redirect URIs |
| `OAUTH_DISCORD_CLIENT_ID/SECRET` | — | Discord app credentials |

### Running
```bash
cd apps/api
pip install -e ".[test]"
uvicorn app.main:app --reload          # in-memory mode
DATABASE_URL=... PERSISTENCE_BACKEND=postgres uvicorn app.main:app --reload
pytest                                  # tests (in-memory)
dndmap-db migrate && dndmap-db seed     # init postgres
```

### File layout
```
app/
  main.py          # create_app factory, lifespan
  core/config.py   # Settings (pydantic-settings)
  db/
    base.py        # DeclarativeBase
    engine.py      # make_engine, make_session_factory
    session.py     # get_db dependency, DbSession
    models.py      # SQLAlchemy ORM (User → MapExport)
  auth/
    jwt.py         # mint_token, decode_token
    cookie.py      # set/clear/get cookie helpers
    state.py       # sign_state, verify_state (itsdangerous)
    providers.py   # Discord, Google, GitHub adapters
    dependencies.py # CurrentUser, get_campaign_member
  domain/
    models.py      # domain dataclasses (Campaign, Layer, etc.)
    schemas.py     # Pydantic I/O schemas
  repositories/
    base.py        # MapDataStore async Protocol
    in_memory.py   # InMemoryMapStore (asyncio.Lock)
    postgres.py    # PostgresMapStore (SQLAlchemy)
  api/routes/
    auth.py        # /auth/{provider}/login|callback, /auth/logout, /auth/me
    invites.py     # /campaigns/{id}/invites, /invites/{code}/accept
    campaigns.py   # /campaigns CRUD
    maps.py        # /campaigns/{id}/maps, /maps CRUD
    layers.py      # /maps/{id}/layers, /layers CRUD
    objects.py     # /maps/{id}/objects, /objects CRUD
    exports.py     # /maps/{id}/exports, /exports
    realtime.py    # WS /ws/campaigns/{id}/maps/{id}
  cli/db.py        # dndmap-db migrate|seed|reset
alembic/           # Alembic migrations
```

## Frontend (`apps/web/`)

> **Current state**: The frontend has TanStack Query, auth providers, login/campaign/invite routes, and a hosted map editor route wired to backend maps, layers, objects, and image upload. It still contains the original SVG-based map editor; Track C below is the target Konva rewrite.

### Track C — Konva canvas rewrite (not started)

Replace the SVG editor with React Konva. New packages needed: `react-konva`, `konva`, `use-image`.

**Files to create:**
- `hooks/useMapState.ts` — object/tool/title state extracted from MapEditor
- `hooks/useMapViewport.ts` — zoom/pan/coord math
- `components/map/MapCanvas.tsx` — Konva Stage/Layer render tree (`"use client"`)
- `components/map/MapToolbar.tsx` — tool palette
- `components/map/ObjectPanel.tsx` — object properties panel
- `components/map/LayerPanel.tsx` — layer list sidebar

**Files to rewrite:**
- `components/MapEditor.tsx` — becomes an orchestration shell composing the above
- `app/page.tsx` — load MapEditor via `dynamic(..., { ssr: false })`
- `lib/pdfExport.ts` — replace Canvas2D with `stage.toCanvas({ pixelRatio: 2 })`

### Track D — Auth + routing (started)

Wire frontend to the backend auth system. New packages needed: `@tanstack/react-query@^5`.

Implemented baseline:
- `lib/api.ts` — `apiFetch<T>()` with `credentials: "include"`, typed `api.*` wrappers
- `components/providers/QueryProvider.tsx` and `AuthProvider.tsx`
- `app/login/page.tsx`, `app/campaigns/page.tsx`, `app/campaigns/[id]/page.tsx`, `app/invite/[code]/page.tsx`
- `app/campaigns/[id]/maps/[mapId]/page.tsx` with hosted SVG editor persistence
- `middleware.ts` for auth-cookie protected campaign/invite routes
- `app/api/campaigns/route.ts` removed in favor of direct API calls

### Key conventions (target state)
- `"use client"` required on all Konva components and components using hooks
- `MapEditor` loaded via `dynamic(..., { ssr: false })` — Konva reads `window` at import
- All API calls: `lib/api.ts` → `apiFetch<T>()` with `credentials: "include"`
- Auth state: `useAuth()` from `AuthProvider`; components never read cookies directly
- TanStack Query staleTime: 30s
- Query key conventions: `["campaigns"]`, `["campaigns", id]`, `["campaigns", id, "maps"]`, `["maps", mapId, "layers"]`, `["maps", mapId, "objects", filters]`, `["auth", "me"]`

### Canvas approach
React Konva (`react-konva` + `konva`). Use `<Stage>`, `<Layer>`, `<Circle>`, `<Text>`, `<Line>`, `<Image>`, `<Transformer>`.

## ADRs

1. **Async repos**: `MapDataStore` is an async Protocol. All implementations must be `async def`. Enables SQLAlchemy asyncio without fighting FastAPI.
2. **JWT = sub only**: JWT payload is `{sub: user_id}`. Roles queried from `campaign_members` table per-request — avoids stale membership in token.
3. **No Next.js BFF proxy**: Frontend hits nginx → FastAPI directly. Cookies are same-origin. The old `app/api/campaigns/route.ts` proxy is removed.
4. **Konva + ssr:false**: Konva references `window` at import time. Always load `MapEditor` with `dynamic(..., { ssr: false })`.
5. **OAuth state signed**: `itsdangerous.URLSafeTimedSerializer` signs a nonce into the `state` param. Cookie `SameSite=lax` (not strict, which would break the OAuth redirect).

## Multi-agent notes

See `AGENTS.md` for module ownership and coordination rules.
