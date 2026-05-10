# Contributing — Local Dev Loop

## Prerequisites

- Docker Desktop (for Postgres, Redis, MinIO)
- Python 3.12+
- Node.js 20+

## Backend setup

```bash
cd apps/api

# Install with dev/test deps
pip install -e ".[test]"

# Start backing services (Postgres, Redis, MinIO)
docker compose up -d postgres redis minio

# Run database migrations
DATABASE_URL=postgresql+asyncpg://dndmap:dndmap_dev_password@localhost:5432/dndmap \
  dndmap-db migrate

# Seed dev fixtures (1 user, 1 campaign, 1 map)
DATABASE_URL=postgresql+asyncpg://dndmap:dndmap_dev_password@localhost:5432/dndmap \
  dndmap-db seed

# Run API (Postgres mode)
DATABASE_URL=postgresql+asyncpg://dndmap:dndmap_dev_password@localhost:5432/dndmap \
PERSISTENCE_BACKEND=postgres \
SESSION_SECRET=dev-session-secret-at-least-32-chars \
JWT_SECRET=dev-jwt-secret-at-least-32-chars \
AUTH_ENABLED=true \
  uvicorn app.main:app --reload

# Run API (in-memory mode, no Postgres needed)
uvicorn app.main:app --reload
```

## Running tests

```bash
cd apps/api
pytest               # fast — in-memory store

# Postgres integration tests (requires running Postgres)
POSTGRES_TEST_URL=postgresql+asyncpg://dndmap:dndmap_dev_password@localhost:5432/dndmap_test \
  pytest -m integration
```

## Frontend setup

```bash
cd apps/web
npm install
npm run dev          # starts at http://localhost:3000
npm run typecheck    # TypeScript check
npm run lint         # ESLint
```

## Discord OAuth setup (local)

1. Go to https://discord.com/developers/applications
2. Create a new application
3. Under OAuth2 → Redirects, add: `http://localhost:8080/api/v1/auth/discord/callback`
4. Copy Client ID and Client Secret
5. Set in your `.env` file (copy `.env.example` → `.env`):
   ```
   AUTH_ENABLED=true
   OAUTH_DISCORD_CLIENT_ID=your_client_id
   OAUTH_DISCORD_CLIENT_SECRET=your_client_secret
   OAUTH_REDIRECT_BASE_URL=http://localhost:8080/api/v1/auth
   SESSION_SECRET=your-random-32-char-secret
   JWT_SECRET=your-random-32-char-jwt-secret
   ```

## Full stack (Docker Compose)

```bash
# Copy and edit env file
cp .env.example .env
# Edit .env with your Discord credentials

# Start everything
docker compose up --build

# Visit http://localhost:8080
```

Services:
- `http://localhost:8080` — nginx (routes /api/* to backend, rest to frontend)
- `http://localhost:8000` — FastAPI directly
- `http://localhost:3000` — Next.js directly
- `http://localhost:9001` — MinIO console

## Database reset

```bash
DATABASE_URL=postgresql+asyncpg://dndmap:dndmap_dev_password@localhost:5432/dndmap \
  dndmap-db reset
```

## Adding a migration

```bash
cd apps/api
DATABASE_URL=postgresql+asyncpg://dndmap:dndmap_dev_password@localhost:5432/dndmap \
  alembic revision --autogenerate -m "describe your change"
# Review the generated file in alembic/versions/
# Run dndmap-db migrate to apply
```
