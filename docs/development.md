# Developer Setup

This project is scaffolded for a FastAPI API, a Next.js web UI, Postgres, Redis, and MinIO. The first iteration uses in-memory API storage for fast local development while keeping the service boundaries ready for Postgres, Redis, and S3-backed persistence.

## Prerequisites

- Docker Desktop or Docker Engine with Compose v2
- Python 3.12 for native API development
- Node.js 20 for native web development

## Environment

Create a local environment file from the checked-in template:

```powershell
Copy-Item .env.example .env
```

The values in `.env.example` are development defaults only. Rotate every secret before using a shared or production environment.

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

## Full Docker App Stack

After the API and web app directories exist, build and run everything through Compose:

```powershell
docker compose --profile app up -d --build
```

The app profile starts:

- `api` on `http://localhost:8000`
- `web` on `http://localhost:3000`
- `proxy` on `http://localhost:8080`

## Reset Local Data

To stop containers while keeping volumes:

```powershell
docker compose down
```

To remove local database, Redis, and MinIO data:

```powershell
docker compose down -v
```
