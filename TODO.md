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

Recommended next implementation order:

1. Harden the WebSocket contract before adding more editor features:
   - authenticate WebSocket connections from the `access_token` cookie when `AUTH_ENABLED=true`
   - reject non-members and map/campaign mismatches with policy-close responses
   - add a stable event envelope with `id`, `type`, `map_id`, `actor`, `payload`, and `sent_at`
   - keep REST APIs as the source of persisted truth; use WebSockets for presence, locks, and invalidation/broadcast events
2. Add Redis-backed realtime coordination:
   - move map event fanout from in-process memory to Redis pub/sub
   - keep an in-memory fallback for tests and single-process local development
   - add presence join/leave/snapshot messages so users can see who is on a map
3. Wire the hosted editor to realtime:
   - connect from `app/campaigns/[id]/maps/[mapId]`
   - show online collaborators in the toolbar
   - after save/upload/layer changes, broadcast invalidation events
   - when another user changes the map, invalidate TanStack Query keys and refetch map/layers/objects
4. Add object locking:
   - lock while dragging/editing an object
   - expire locks with a Redis TTL so abandoned locks clear automatically
   - show who is editing a marker/path/label and prevent conflicting writes in the UI
5. Add revision history:
   - create a `map_revisions` migration and repository methods
   - write a revision on object create/update/delete, layer visibility changes, and map image changes
   - expose `GET /maps/{id}/revisions` with actor, timestamp, summary, and changed object IDs
6. Move exports server-side:
   - enqueue export jobs
   - generate PNG/PDF artifacts with DM/player visibility rules
   - store generated artifacts in S3/MinIO and return presigned URLs

- [ ] Move WebSocket fanout onto Redis pub/sub so multiple API instances share broadcast state
- [ ] Add presence indicators (who is connected to a map)
- [ ] Implement object locking while a user is dragging
- [ ] Add revision history writes on object mutation
- [ ] Implement export job workers that generate server-side PNG/PDF respecting DM/player visibility
- [ ] Add rate limits on auth, upload, and mutation-heavy endpoints

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

- [ ] Pin image tags/digests in `docker-compose.yml` for reproducible production builds
- [ ] Add TLS termination docs and example Caddy / Traefik config
- [ ] Write migration runbook (pre-deploy checklist, rollback steps)
- [ ] Add backup and restore smoke test for Postgres and MinIO
- [ ] Set up structured logging and error alerting for the API
- [ ] Document secret rotation procedure for OAuth credentials and `SESSION_SECRET`
