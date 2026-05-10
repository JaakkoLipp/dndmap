# D&D Campaign Map

Greenfield implementation for a self-hosted D&D campaign map web UI.

The application is a Python FastAPI API plus a Next.js web app, backed by Postgres, Redis, and S3-compatible object storage through MinIO. The first iteration includes a usable local map editor, a structured API skeleton, and deployment scaffolding for Docker or native development.

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

## App Layout

The compose and Docker scaffolding expects future app code in these paths:

```text
apps/
  api/   # FastAPI project, ASGI app defaults to app.main:app
  web/   # Next.js project
```
