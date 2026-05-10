# Self-Hosted Deployment

The deployment scaffold is Docker Compose based. It is suitable for a single host or small private server running the FastAPI API, Next.js web app, Postgres, Redis, and MinIO together.

This is not yet the complete hosted product mode. The current app slice can run behind the included proxy, but durable persistence, auth, migrations, and background processing are planned completion work before treating the stack as production-ready.

## Server Prerequisites

- A Linux host with Docker Engine and Compose v2
- DNS pointing at the host
- TLS termination through a host reverse proxy such as Caddy, Traefik, nginx, or a managed load balancer
- Persistent disk space for Postgres and MinIO volumes

## Production Environment

Create `.env` from `.env.example` and replace all development defaults:

```bash
cp .env.example .env
```

At minimum, rotate:

- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`
- `SESSION_SECRET`
- all OAuth provider client secrets
- public URLs such as `PUBLIC_SITE_URL` and `NEXT_PUBLIC_API_BASE_URL`

For production, set API container URLs to Docker-internal service names:

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@postgres:5432/DBNAME
REDIS_URL=redis://:PASSWORD@redis:6379/0
S3_ENDPOINT_URL=http://minio:9000
S3_PUBLIC_ENDPOINT_URL=https://files.example.com
```

Set hosted auth variables when OAuth is enabled:

```dotenv
AUTH_ENABLED=true
AUTH_OAUTH_PROVIDERS=discord,google,github
OAUTH_REDIRECT_BASE_URL=https://maps.example.com/api/auth/callback
OAUTH_DISCORD_CLIENT_ID=...
OAUTH_DISCORD_CLIENT_SECRET=...
OAUTH_GOOGLE_CLIENT_ID=...
OAUTH_GOOGLE_CLIENT_SECRET=...
OAUTH_GITHUB_CLIENT_ID=...
OAUTH_GITHUB_CLIENT_SECRET=...
```

The current code may ignore some hosted-mode variables until the matching product milestone lands. Keep the variables configured anyway so deployment, secret storage, and provider callback URLs can be tested early.

## Launch

Build and run the full stack:

```bash
docker compose --profile app up -d --build
```

The included `proxy` service exposes the app over plain HTTP on `HTTP_PORT` and forwards:

- `/api/` to FastAPI
- `/` to Next.js

Terminate TLS in front of this proxy, or replace it with your preferred ingress layer.

## Migrations

Run database migrations from the API container after deploys once the Postgres repository is implemented. The exact command depends on the API implementation, for example:

```bash
docker compose --profile app exec api alembic upgrade head
```

## Backups

Back up Postgres with `pg_dump` from the host or from inside the container:

```bash
docker compose exec postgres sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backup.sql
```

Back up MinIO by syncing the configured bucket to durable storage with the MinIO client (`mc mirror`) from a trusted admin workstation or scheduled backup job.

For production, schedule automated Postgres dumps and object storage replication outside the app deploy process.

## Upgrades

1. Pull the latest application code.
2. Review `.env.example` for new variables and update `.env`.
3. Rebuild and restart:

   ```bash
   docker compose --profile app up -d --build
   ```

4. Run migrations.
5. Check container health:

   ```bash
   docker compose ps
   docker compose logs --tail=100 api web proxy
   ```

## Operational Notes

- Pin image tags or digests before production hardening, especially for MinIO and nginx.
- Keep Postgres, Redis, and MinIO ports firewalled from the public internet.
- Store `.env` outside version control and restrict file permissions on the server.
- Monitor disk usage for the Docker volumes `postgres-data`, `redis-data`, and `minio-data`.
- Use a real S3-compatible bucket for multi-host deployments; the included MinIO service is best for local development and small single-host installs.
- Enable OAuth only over HTTPS with exact redirect URIs registered at Discord, Google, and GitHub.
- Run API tests, web type checks, Compose config validation, and a smoke deploy before promoting a hosted release.
