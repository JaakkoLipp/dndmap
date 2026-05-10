# D&D Campaign Map API

FastAPI backend for the self-hosted campaign map app.

## Running

```bash
pip install -e ".[test]"

# In-memory mode (no Postgres required)
uvicorn app.main:app --reload

# Postgres mode
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dndmap \
PERSISTENCE_BACKEND=postgres \
AUTH_ENABLED=true \
JWT_SECRET=<32+ char secret> \
SESSION_SECRET=<32+ char secret> \
uvicorn app.main:app --reload
```

## Database

```bash
dndmap-db migrate   # run Alembic migrations
dndmap-db seed      # insert dev seed data
dndmap-db reset     # drop all tables and re-migrate (dev only)
```

## Tests

```bash
pytest                                              # in-memory store, 56 tests
pytest -k "test_auth"                               # auth only
POSTGRES_TEST_URL=postgresql+asyncpg://... pytest -m integration  # postgres
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `PERSISTENCE_BACKEND` | `memory` | `memory` or `postgres` |
| `DATABASE_URL` | — | `postgresql+asyncpg://user:pass@host/db` |
| `AUTH_ENABLED` | `false` | Enable JWT auth guard on all routes |
| `JWT_SECRET` | — | HS256 signing key (32+ chars) |
| `JWT_EXPIRE_MINUTES` | `60` | Token lifetime |
| `SESSION_SECRET` | — | OAuth state HMAC key (32+ chars) |
| `OAUTH_REDIRECT_BASE_URL` | `http://localhost:8080/api/v1/auth` | Base for OAuth redirect URIs |
| `OAUTH_DISCORD_CLIENT_ID` | — | Discord app client ID |
| `OAUTH_DISCORD_CLIENT_SECRET` | — | Discord app client secret |
| `OAUTH_GOOGLE_CLIENT_ID` | — | Google app client ID |
| `OAUTH_GOOGLE_CLIENT_SECRET` | — | Google app client secret |
| `OAUTH_GITHUB_CLIENT_ID` | — | GitHub app client ID |
| `OAUTH_GITHUB_CLIENT_SECRET` | — | GitHub app client secret |

## Auth notes

- `AUTH_ENABLED=false` (default): all routes are open, no DB needed. Good for local dev / tests.
- `AUTH_ENABLED=true`: routes that use `CurrentUser` return 401 without a valid `access_token` cookie. Routes that use `OptionalCurrentUser` work without auth but apply RBAC when a user is present.
- JWT payload: `{"sub": user_id}`. Roles are **never** embedded in the token — they are queried from `campaign_members` per request.

## OpenAPI docs

`http://localhost:8000/docs` (direct) or `http://localhost:8080/api/v1/docs` (through nginx).
