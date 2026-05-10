# Self-Hosted Deployment

The deployment scaffold is Docker Compose based. It is suitable for a single host or small private server running the FastAPI API, Next.js web app, Postgres, Redis, and MinIO together.

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
- public URLs such as `PUBLIC_SITE_URL` and `NEXT_PUBLIC_API_BASE_URL`

For production, set API container URLs to Docker-internal service names:

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@postgres:5432/DBNAME
REDIS_URL=redis://:PASSWORD@redis:6379/0
S3_ENDPOINT_URL=http://minio:9000
S3_PUBLIC_ENDPOINT_URL=https://files.example.com
```

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

Run database migrations from the API container after deploys. The exact command depends on the API implementation, for example:

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
