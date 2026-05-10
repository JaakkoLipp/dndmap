# D&D Campaign Map

Greenfield implementation for a D&D campaign map web UI.

The application is a Python FastAPI API plus a Next.js web app. The repository includes Docker scaffolding for Postgres, Redis, and S3-compatible object storage through MinIO. The backend now supports Postgres persistence, OAuth/RBAC, invites, and durable map image upload; the frontend has the first hosted campaign/auth routes while the editor is still the original SVG implementation.

## Current Status

Current capabilities:

- Local map editor with image loading, pan/zoom, category-aware known locations, labels, routes, and freehand trails.
- DM/player visibility controls for map notes in the editor.
- Browser-side PNG and PDF export of the current map view, plus full-map PNG export.
- FastAPI resources for campaigns, maps, layers, objects, export jobs, health checks, OAuth, invites, and map WebSocket broadcasts.
- Postgres-backed persistence with Alembic migrations and local seed/reset commands.
- S3/MinIO-backed map image upload with presigned image URLs on map reads.
- Hosted frontend shell for login, campaigns, campaign detail, invites, and persisted map editor routes.
- Authenticated WebSocket realtime: cookie-gated, campaign-membership-checked, presence snapshot + join/leave events, REST mutations publish invalidation events for connected editors, Redis pub/sub fanout across API replicas with an in-memory fallback.
- Live presence indicator in the hosted editor: collaborator avatars and a connection-state pill.
- Rate limits on auth callback, map image upload, and mutation endpoints (Redis-backed when configured, otherwise in-memory).
- Operations runbook covering TLS, migrations, backups, secret rotation, observability, and incident response.

Planned complete hosted mode:

- React Konva editor rewrite and richer layer controls.
- Server-side export jobs with DM/player visibility, presigned download URLs, and persistent revision history.
- Object locks during drag/edit and conflict-aware multi-user editing.
- Production CI smoke tests for Docker Compose, OAuth flows, and realtime sync.

## Next Product Slice

With realtime and rate limits landed, the next implementation pass focuses on persistent collaboration semantics and the editor surface:

1. Add Redis-backed object locks while a user drags or edits a marker, with TTLs that clear abandoned locks.
2. Add a `map_revisions` migration and revision-writes on object mutations to power audit and undo flows.
3. Move PNG/PDF exports server-side with DM/player visibility and presigned download URLs.
4. Rewrite the SVG editor to React Konva (`MapCanvas.tsx`, `useMapState.ts`, `useMapViewport.ts`) and surface live collaborator cursors.
5. Finish OAuth provider production setup docs and add a Playwright smoke covering login → campaign creation → map upload → realtime sync.

## Quick Start

1. Copy the environment template:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Start local backing services:

   ```powershell
   docker compose up -d postgres redis minio minio-create-bucket
   ```

3. Open service consoles:

   - Postgres: `localhost:5432`
   - Redis: `localhost:6379`
   - MinIO API: `http://localhost:9000`
   - MinIO console: `http://localhost:9001`

4. Run the full app stack:

   ```powershell
   docker compose --profile app up -d --build
   ```

The default reverse proxy listens on `http://localhost:8080` when the `app` profile is enabled.

## Documentation

- [Developer setup](docs/development.md)
- [Self-hosted deployment](docs/deployment.md)
- [Operations runbook](docs/operations.md)
- [Hosted mode roadmap](docs/roadmap.md)

## App Layout

The compose and Docker scaffolding expects app code in these paths:

```text
apps/
  api/   # FastAPI project, ASGI app defaults to app.main:app
  web/   # Next.js project
```
