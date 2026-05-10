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
- Docker Compose services for the API, web app, Postgres, Redis, MinIO, and nginx reverse proxy.

Planned complete hosted mode:

- React Konva editor rewrite and richer layer controls.
- S3-compatible storage for thumbnails and export artifacts.
- Redis-backed sessions, presence, pub/sub, rate limits, and background job coordination.
- Production runbooks for backups, deploys, migrations, observability, and hosted environment rotation.

## Next Product Slice

The next implementation pass should focus on making hosted maps feel genuinely multi-user before expanding the drawing surface:

1. Harden `WS /api/v1/ws/campaigns/{campaign_id}/maps/{map_id}` with auth, membership checks, and a stable realtime event envelope.
2. Move WebSocket fanout to Redis pub/sub while keeping the in-memory path for tests and local single-process development.
3. Add presence events and a hosted-editor presence indicator so DMs and players can see who is viewing a map.
4. Broadcast map/object/layer invalidation events after REST persistence succeeds, then have other open editors refetch through TanStack Query.
5. Add Redis-backed object locks and revision history before sending direct object mutation payloads over WebSocket.
6. Finish Discord OAuth production setup docs and smoke tests with real redirect URIs.

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
- [Hosted mode roadmap](docs/roadmap.md)

## App Layout

The compose and Docker scaffolding expects app code in these paths:

```text
apps/
  api/   # FastAPI project, ASGI app defaults to app.main:app
  web/   # Next.js project
```
