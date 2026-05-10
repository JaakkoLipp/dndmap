# TODO

What is still needed to reach a complete hosted product.

## Persistence (Milestone 2) ✓

- [x] Add SQLAlchemy models for `User`, `OAuthIdentity`, `Campaign`, `CampaignMember`, `CampaignInvite`, `CampaignMap`, `MapLayer`, `MapObjectRow`, `MapExport`
- [x] Write Alembic migration for the initial schema (`alembic/versions/0001_initial_schema.py`)
- [x] Implement a Postgres-backed repository (`app/repositories/postgres.py`) satisfying the async `MapDataStore` protocol
- [x] Switch `create_app` to select the Postgres repo when `PERSISTENCE_BACKEND=postgres`
- [x] Add `dndmap-db migrate / seed / reset` CLI commands
- [ ] Wire map objects from the editor into the API save flow (currently only campaign + map metadata are persisted)

## Asset Storage (Milestone 3)

- [x] Add `POST /maps/{id}/image` upload endpoint that streams to S3/MinIO
- [x] Generate presigned download URLs for stored map images
- [x] Replace in-browser `data:` image state with an S3 object key + URL round-trip in hosted editor routes
- [ ] Generate presigned download URLs for export artifacts
- [ ] Normalize object coordinates relative to image dimensions on save so exports are resolution-stable

## Auth & Permissions (Milestone 4)

### Backend ✓

- [x] Add `sqlalchemy[asyncio]`, `asyncpg`, `python-jose`, `itsdangerous`, `httpx`, `respx` to `pyproject.toml`
- [x] Implement `GET /auth/{provider}/login`, `GET /auth/{provider}/callback`, `POST /auth/logout`, `GET /auth/me` for Discord, Google, and GitHub
- [x] Store JWT in HTTP-only cookie; OAuth state param signed with `itsdangerous`
- [x] Enforce campaign roles (owner / dm / player / viewer) on all API routes
- [x] Implement invite link flow: `POST /campaigns/{id}/invites`, `POST /invites/{code}/accept`
- [x] Role-check and invite-acceptance unit tests (56 passing)

### Frontend (hosted shell started)

- [ ] Rewrite SVG map editor to React Konva (`MapCanvas.tsx`, `useMapState.ts`, `useMapViewport.ts`)
- [x] Add TanStack Query (`@tanstack/react-query@^5`) and typed API client (`lib/api.ts`)
- [x] Add `QueryProvider` + `AuthProvider` wrappers in `app/layout.tsx`
- [x] Add login page (`app/login/page.tsx`) with Discord / Google / GitHub OAuth buttons
- [x] Add `middleware.ts` to redirect unauthenticated users to `/login`
- [x] Add campaign list page (`app/campaigns/page.tsx`) with TanStack Query
- [x] Add campaign detail page (`app/campaigns/[id]/page.tsx`) with invite management (DM only)
- [x] Add invite acceptance page (`app/invite/[code]/page.tsx`)
- [x] Add map editor route (`app/campaigns/[id]/maps/[mapId]/page.tsx`)
- [ ] Discord / Google / GitHub developer apps: configure redirect URIs and set credentials in `.env`

## Realtime & Jobs (Milestone 5)

Slices done (see `apps/api/app/realtime/`):

- [x] Authenticate WebSocket connections from the `access_token` cookie when `AUTH_ENABLED=true`; reject non-members with `1008` policy close.
- [x] Stable event envelope `{id, type, map_id, actor, payload, sent_at}`.
- [x] Redis pub/sub broker with in-memory fallback for tests / single-process dev.
- [x] Presence snapshot/joined/left events.
- [x] Publish realtime invalidation events from REST map / layer / object mutations.
- [x] Hosted editor realtime client: presence pill, auto-reconnect, TanStack Query invalidation on remote changes.
- [x] Rate limits on auth callback, image upload, and mutation endpoints (Redis-backed with in-memory fallback).

Still open:

- [ ] Implement object locking while a user is dragging (Redis TTL keys, UI lock indicators).
- [x] Add revision history writes on object mutation (`map_revisions` migration + `GET /maps/{id}/revisions`). Frontend has a collapsible Recent Activity panel in the hosted editor.
- [ ] Implement export job workers that generate server-side PNG/PDF respecting DM/player visibility.
- [ ] Cross-process presence snapshot (currently snapshot is per-API-process).

## Editor Features

- [ ] Add realtime WebSocket client in the hosted editor:
  - connect to `WS /ws/campaigns/{campaign_id}/maps/{map_id}`
  - render connection state and online users
  - refetch map/layer/object queries on remote changes
  - broadcast local save/upload changes after REST persistence succeeds
- [ ] Add polygon / area drawing tool to the frontend toolbar
- [ ] Add handout tool (linked image or text note on the map)
- [ ] Wire layer model into the UI (layer picker, DM-only / player-visible / hidden states)
- [x] Persist existing editor annotations through backend map object APIs in hosted editor routes
- [ ] Add player-visible export option (renders only player-visible objects)

## Tests

- [x] Backend: role-check unit tests (`test_rbac.py`)
- [x] Backend: invite-acceptance unit tests (`test_invites.py`)
- [x] Backend: map image upload and presigned URL tests
- [ ] Backend: WebSocket rejection for unauthorized users and reconnect sync
- [ ] Backend: export visibility tests (DM vs. player output)
- [ ] Frontend: component tests for tool selection, layer toggles, permission-gated controls
- [ ] Frontend: Playwright tests for login, campaign creation, map upload, annotation editing, realtime multi-tab sync, export
- [ ] CI: Docker Compose smoke test (boot all services, hit `/health`, load the editor)

## Operations (Milestone 6)

- [x] Pin image tags in `docker-compose.yml` (MinIO server + mc pinned to dated releases; nginx already pinned)
- [x] TLS termination docs with Caddy and Traefik examples (`docs/operations.md`)
- [x] Migration runbook with pre-deploy checklist and rollback steps (`docs/operations.md`)
- [x] Backup / restore procedure for Postgres and MinIO, plus quarterly smoke-test process (`docs/operations.md`)
- [x] Secret rotation procedure for OAuth credentials, `SESSION_SECRET`, and `JWT_SECRET` (`docs/operations.md`)
- [ ] Wire structured logging + error alerting from API logs to your aggregator
- [ ] Pin image digests (not just tags) for fully reproducible production builds
