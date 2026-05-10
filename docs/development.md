# Developer Setup

This project is scaffolded for a FastAPI API, a Next.js web UI, Postgres, Redis, and MinIO. The current iteration is a local-first product slice: the API uses in-memory storage, and the web draft save path is stubbed through the Next.js app. The Compose services are already present so the next iteration can move into durable hosted mode without reshaping the development workflow.

## Current Capabilities

- Web editor: load a local image, pan/zoom, add category-aware known locations, labels, routes, and freehand trails, edit map note properties, control DM/player visibility, and export the current view or full map.
- API scaffold: health checks plus CRUD-style routes for campaigns, maps, layers, objects, export jobs, and map WebSocket broadcasts under `/api/v1`.
- Local infrastructure: Postgres, Redis, MinIO, and nginx are available through Compose.

Current limitations:

- Campaign and map API data is not durable; restarting the API clears the in-memory store.
- Uploaded map images remain browser-local until the S3 upload flow is implemented.
- Auth, user accounts, memberships, permissions, background export workers, and production migrations are planned work.

## Prerequisites

- Docker Desktop or Docker Engine with Compose v2
- Python 3.11 or newer for native API development; Python 3.12 is recommended
- Node.js 20 and npm for native web development
- PowerShell 7 or Windows PowerShell for the commands below, or equivalent shell commands on macOS/Linux
- Optional: MinIO client (`mc`) for manual bucket inspection and backup testing

## Environment

Create a local environment file from the checked-in template:

```powershell
Copy-Item .env.example .env
```

The values in `.env.example` are development defaults only. Rotate every secret before using a shared or production environment.

Several auth and persistence variables are documented before the app consumes all of them. Keep them in `.env` so local, CI, and hosted environments converge as the implementation catches up.

## Start Backing Services

Run Postgres, Redis, MinIO, and the bucket bootstrap job:

```powershell
docker compose up -d postgres redis minio minio-create-bucket
```

Useful local endpoints:

| Service | URL / address |
| --- | --- |
| Postgres | `localhost:5432` |
| Redis | `localhost:6379` |
| MinIO API | `http://localhost:9000` |
| MinIO console | `http://localhost:9001` |

The default MinIO console login is `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` from `.env`.

## Native API Development

Run the API natively against the Compose services:

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
$env:DATABASE_URL = "postgresql+psycopg://dndmap:dndmap_dev_password@localhost:5432/dndmap"
$env:REDIS_URL = "redis://:dndmap_redis_dev_password@localhost:6379/0"
$env:S3_ENDPOINT_URL = "http://localhost:9000"
$env:S3_BUCKET = "dnd-campaign-map"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run API tests:

```powershell
cd apps/api
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
pytest
```

If the API uses `requirements.txt` instead of `pyproject.toml`, install with `python -m pip install -r requirements.txt`.

## Native Web Development

Run the web app natively:

```powershell
cd apps/web
npm install
$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000"
npm run dev
```

Use the package manager and lockfile selected by the web app implementation if it differs from `npm`.

Run web checks:

```powershell
cd apps/web
npm run typecheck
npm run build
```

Use `npm run lint` once the Next.js lint command is wired for the selected framework version.

## Full Docker App Stack

After the API and web app directories exist, build and run everything through Compose:

```powershell
docker compose --profile app up -d --build
```

The app profile starts:

- `api` on `http://localhost:8000`
- `web` on `http://localhost:3000`
- `proxy` on `http://localhost:8080`

## Auth and OAuth Plan

The current app has no authentication. Hosted mode is expected to add:

- Discord OAuth as the primary campaign-group login provider.
- Google OAuth for broad consumer/team login support.
- GitHub OAuth for admin and contributor convenience.
- Secure HTTP-only session cookies, CSRF protection for browser mutations, and per-campaign roles such as owner, GM, player, and viewer.

Provider client IDs and secrets belong in `.env`; never expose secrets through `NEXT_PUBLIC_*` variables.

## Persistence Plan

- Postgres is the source of truth for users, OAuth identities, campaigns, maps, layers, objects, memberships, export job metadata, and audit timestamps.
- S3-compatible storage is used for uploaded map images, generated thumbnails, export files, and future import bundles. Local development uses MinIO with the same bucket contract.
- Redis is used for session lookup/cache data, WebSocket presence, pub/sub fanout, job coordination, and rate limiting.
- The API should keep the repository boundary intact so tests can continue using an in-memory adapter while hosted mode uses a Postgres-backed adapter.

## Reset Local Data

To stop containers while keeping volumes:

```powershell
docker compose down
```

To remove local database, Redis, and MinIO data:

```powershell
docker compose down -v
```
