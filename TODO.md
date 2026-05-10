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

- [ ] Add `POST /maps/{id}/image` upload endpoint that streams to S3/MinIO
- [ ] Generate presigned download URLs for stored images and export artifacts
- [ ] Replace in-browser `data:` image state with an S3 object key + URL round-trip
- [ ] Normalize object coordinates relative to image dimensions on save so exports are resolution-stable

## Auth & Permissions (Milestone 4)

### Backend ✓

- [x] Add `sqlalchemy[asyncio]`, `asyncpg`, `python-jose`, `itsdangerous`, `httpx`, `respx` to `pyproject.toml`
- [x] Implement `GET /auth/{provider}/login`, `GET /auth/{provider}/callback`, `POST /auth/logout`, `GET /auth/me` for Discord, Google, and GitHub
- [x] Store JWT in HTTP-only cookie; OAuth state param signed with `itsdangerous`
- [x] Enforce campaign roles (owner / dm / player / viewer) on all API routes
- [x] Implement invite link flow: `POST /campaigns/{id}/invites`, `POST /invites/{code}/accept`
- [x] Role-check and invite-acceptance unit tests (56 passing)

### Frontend (not started)

- [ ] Rewrite SVG map editor to React Konva (`MapCanvas.tsx`, `useMapState.ts`, `useMapViewport.ts`)
- [ ] Add TanStack Query (`@tanstack/react-query@^5`) and typed API client (`lib/api.ts`)
- [ ] Add `QueryProvider` + `AuthProvider` wrappers in `app/layout.tsx`
- [ ] Add login page (`app/login/page.tsx`) with Discord / Google / GitHub OAuth buttons
- [ ] Add `middleware.ts` to redirect unauthenticated users to `/login`
- [ ] Add campaign list page (`app/campaigns/page.tsx`) with TanStack Query
- [ ] Add campaign detail page (`app/campaigns/[id]/page.tsx`) with invite management (DM only)
- [ ] Add invite acceptance page (`app/invite/[code]/page.tsx`)
- [ ] Add map editor route (`app/campaigns/[id]/maps/[mapId]/page.tsx`)
- [ ] Discord / Google / GitHub developer apps: configure redirect URIs and set credentials in `.env`

## Realtime & Jobs (Milestone 5)

- [ ] Move WebSocket fanout onto Redis pub/sub so multiple API instances share broadcast state
- [ ] Add presence indicators (who is connected to a map)
- [ ] Implement object locking while a user is dragging
- [ ] Add revision history writes on object mutation
- [ ] Implement export job workers that generate server-side PNG/PDF respecting DM/player visibility
- [ ] Add rate limits on auth, upload, and mutation-heavy endpoints

## Editor Features

- [ ] Add polygon / area drawing tool to the frontend toolbar
- [ ] Add handout tool (linked image or text note on the map)
- [ ] Wire layer model into the UI (layer picker, DM-only / player-visible / hidden states)
- [ ] Implement realtime WebSocket client in the editor (connect, receive updates, optimistic writes)
- [ ] Add player-visible export option (renders only player-visible objects)

## Tests

- [x] Backend: role-check unit tests (`test_rbac.py`)
- [x] Backend: invite-acceptance unit tests (`test_invites.py`)
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
