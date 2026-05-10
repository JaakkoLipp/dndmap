# TODO

What is still needed to reach a complete hosted product.

## Persistence (Milestone 2)

- [ ] Add SQLAlchemy models for `User`, `OAuthIdentity`, `Campaign`, `CampaignMember`, `CampaignInvite`, `Map`, `MapLayer`, `MapObject`, `MapRevision`, `MapExport`
- [ ] Write Alembic migration for the initial schema
- [ ] Implement a Postgres-backed repository that satisfies the `MapDataStore` protocol
- [ ] Switch `create_app` to select the Postgres repo when `DATABASE_URL` is set
- [ ] Add seed and reset commands for local dev and CI
- [ ] Wire map objects from the editor into the API save flow (currently only campaign + map metadata are persisted)

## Asset Storage (Milestone 3)

- [ ] Add `POST /maps/{id}/image` upload endpoint that streams to S3/MinIO
- [ ] Generate presigned download URLs for stored images and export artifacts
- [ ] Replace in-browser `data:` image state with an S3 object key + URL round-trip
- [ ] Normalize object coordinates relative to image dimensions on save so exports are resolution-stable

## Auth & Permissions (Milestone 4)

- [ ] Add `authlib`, `httpx`, `itsdangerous` to `apps/api/pyproject.toml`
- [ ] Implement `GET /auth/{provider}/login` (redirect), `GET /auth/{provider}/callback` (token exchange + user upsert), `POST /auth/logout`, `GET /auth/me` for Discord, Google, and GitHub
- [ ] Store sessions in HTTP-only cookies; add CSRF protection on state param
- [ ] Enforce campaign roles (owner / GM / player / viewer) on all API routes
- [ ] Implement invite link / code flow: `POST /campaigns/{id}/invites`, `POST /invites/{code}/accept`
- [ ] Add a frontend login page and auth context; redirect unauthenticated users
- [ ] Discord developer app: add redirect URI, set `OAUTH_DISCORD_CLIENT_ID` + `OAUTH_DISCORD_CLIENT_SECRET` in `.env`
- [ ] Google and GitHub: same setup in their respective developer consoles

## Realtime & Jobs (Milestone 5)

- [ ] Move WebSocket fanout onto Redis pub/sub so multiple API instances share broadcast state
- [ ] Add presence indicators (who is connected to a map)
- [ ] Implement object locking while a user is dragging
- [ ] Add revision history writes on object mutation (`MapRevision` records)
- [ ] Implement export job workers that generate server-side PNG/PDF respecting DM/player visibility
- [ ] Add rate limits on auth, upload, and mutation-heavy endpoints

## Editor Features

- [ ] Add polygon / area drawing tool to the frontend toolbar
- [ ] Add handout tool (linked image or text note on the map)
- [ ] Wire layer model into the UI (layer picker, DM-only / player-visible / hidden states)
- [ ] Implement realtime WebSocket client in the editor (connect, receive updates, optimistic writes)
- [ ] Add player-visible export option (renders only `playerVisible` objects)

## Tests

- [ ] Backend: role-check and invite-acceptance unit tests
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
