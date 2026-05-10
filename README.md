# D&D Campaign Map

Greenfield implementation for a D&D campaign map web UI.

The application is a Python FastAPI API plus a Next.js web app. The repository already includes Docker scaffolding for Postgres, Redis, and S3-compatible object storage through MinIO, but the current product slice still uses in-memory and browser-local behavior in the app code.

## Current Status

Current capabilities:

- Local map editor with image loading, pan/zoom, category-aware known locations, labels, routes, and freehand trails.
- DM/player visibility controls for map notes in the editor.
- Browser-side PNG and PDF export of the current map view, plus full-map PNG export.
- FastAPI resource scaffold for campaigns, maps, layers, objects, export jobs, health checks, and map WebSocket broadcasts.
- Docker Compose services for the API, web app, Postgres, Redis, MinIO, and nginx reverse proxy.

Planned complete hosted mode:

- OAuth sign-in, organization/campaign membership, and GM/player/viewer permissions.
- Postgres-backed durable campaign data and migrations.
- S3-compatible asset storage for map images, uploads, thumbnails, and export artifacts.
- Redis-backed sessions, presence, pub/sub, rate limits, and background job coordination.
- Production runbooks for backups, deploys, migrations, observability, and hosted environment rotation.

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
