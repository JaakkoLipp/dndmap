# Operations Runbook

This document covers running the hosted D&D campaign map stack: TLS,
deploys, migrations, backups, secret rotation, observability, and
incident response. Pair it with [`deployment.md`](./deployment.md) for
the initial install.

## Service Topology

The hosted stack is five long-running services plus an optional bucket
init job:

| Service    | Role                                                                 |
| ---------- | -------------------------------------------------------------------- |
| `api`      | FastAPI app — REST, OAuth, WebSocket realtime                        |
| `web`      | Next.js SSR/CSR frontend                                             |
| `proxy`    | nginx reverse proxy and `/api` ↔ `/` router (TLS terminates upstream) |
| `postgres` | Authoritative durable store                                          |
| `redis`    | Realtime pub/sub, rate limits, future jobs                           |
| `minio`    | S3-compatible bucket for map images and exports                      |

The API process is stateless aside from in-memory connection bookkeeping;
horizontally scale `api` only when `REDIS_URL` is set (otherwise realtime
events do not fan out across replicas).

## TLS Termination

The bundled `proxy` listens on plain HTTP and is intended to sit behind a
TLS terminator on the same host (Caddy, Traefik, or nginx + certbot). The
WebSocket route `/api/v1/ws/...` requires the terminator to forward
`Upgrade` and `Connection` headers correctly.

### Caddy example

```caddyfile
maps.example.com {
    encode zstd gzip

    @ws {
        path /api/v1/ws/*
    }
    reverse_proxy @ws localhost:8080 {
        header_up Host {host}
        header_up X-Real-IP {remote}
        header_up X-Forwarded-For {remote}
        header_up X-Forwarded-Proto {scheme}
    }

    reverse_proxy localhost:8080 {
        header_up Host {host}
        header_up X-Forwarded-For {remote}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

### Traefik (compose snippet)

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.dndmap.rule=Host(`maps.example.com`)"
  - "traefik.http.routers.dndmap.entrypoints=websecure"
  - "traefik.http.routers.dndmap.tls.certresolver=letsencrypt"
  - "traefik.http.services.dndmap.loadbalancer.server.port=80"
```

After enabling TLS, set `APP_ENV=production` so the auth cookie is marked
`Secure`, and update `NEXT_PUBLIC_API_BASE_URL` / `PUBLIC_SITE_URL` to
the `https://` URL.

## Migration Runbook

Database changes are tracked with Alembic. The migration chain is linear
— never branch.

### Pre-deploy checklist

1. Open a maintenance window if the migration:
   - Adds a `NOT NULL` column to a large table (requires backfill).
   - Renames or drops a column referenced by the running API.
   - Adds an index that takes longer than your read-latency SLO allows
     (use `CREATE INDEX CONCURRENTLY` in raw SQL when needed).
2. Take a fresh Postgres dump (see "Backups").
3. Verify all pending migrations apply locally against a copy of
   production: `dndmap-db migrate --offline` to dump SQL, review, then
   apply.
4. Roll out *backwards-compatible* schema first, then code that depends
   on it. For renames / drops, deploy the read-old-write-new code first,
   wait for a quiet window, then drop the legacy column in a follow-up.

### Deploy

```bash
docker compose --profile app pull
docker compose --profile app up -d --build
docker compose --profile app exec api dndmap-db migrate
docker compose --profile app exec api alembic current
```

### Rollback

Code rollback:

```bash
git checkout <previous-tag>
docker compose --profile app up -d --build
```

Schema rollback (only when the previous code can read the new schema):

```bash
docker compose --profile app exec api alembic downgrade -1
```

If `alembic downgrade` is not safe (data loss, irreversible drops),
restore from the pre-deploy Postgres dump instead — see "Backups".

## Backups

### Postgres

Daily logical dumps to durable storage:

```bash
docker compose exec -T postgres \
    pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" \
    > "backups/dndmap-$(date -u +%Y%m%dT%H%M%SZ).dump"
```

Restore:

```bash
docker compose exec -T postgres dropdb -U "$POSTGRES_USER" "$POSTGRES_DB"
docker compose exec -T postgres createdb -U "$POSTGRES_USER" "$POSTGRES_DB"
cat backups/dndmap-YYYYMMDD.dump | docker compose exec -T postgres \
    pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB"
docker compose --profile app exec api dndmap-db migrate
```

### MinIO / S3

Map uploads and (future) export artifacts live in the configured bucket.
Mirror nightly to a second bucket or off-host storage:

```bash
mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc mirror --overwrite --remove local/$S3_BUCKET s3-backup/dndmap
```

### Quarterly smoke test

Restore the most recent dump and bucket mirror into a disposable
environment, run `dndmap-db migrate`, log in as a test user, and verify
that previously uploaded map images still render. Track the result in a
ticket.

## Secret Rotation

| Secret                         | When                                  | How                                                                                                |
| ------------------------------ | ------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `JWT_SECRET`                   | Quarterly, or on compromise           | Generate 64 random chars; update `.env`; restart `api`. Existing sessions log out (expected).      |
| `SESSION_SECRET`               | Quarterly, or on compromise           | Same as `JWT_SECRET`. In-flight OAuth state tokens become invalid (users retry login).             |
| OAuth `*_CLIENT_SECRET`        | On provider rotation or compromise    | Issue a new secret in the provider portal; update `.env`; restart `api`. No user-visible impact.   |
| `POSTGRES_PASSWORD`            | On compromise                         | `ALTER USER` in Postgres, update `.env`, restart `api`. Take a maintenance window.                 |
| `REDIS_PASSWORD`               | On compromise                         | Update `redis-server --requirepass`, `.env`, restart `redis` and `api` together.                   |
| `S3_ACCESS_KEY_ID` / `_SECRET` | On compromise or quarterly            | Issue a new key in MinIO/S3; update `.env`; restart `api`. Old keys can be deleted after rollout.  |

Use `openssl rand -base64 48` to generate replacement values. Update
secrets in your password manager and the deploy host's `.env` file
simultaneously to avoid an outage.

## Observability

Minimum viable monitoring for a hosted deployment:

- **Health checks**: every service has a Compose `healthcheck`. Hook
  `docker compose ps` into your monitoring (Prometheus, Uptime Kuma,
  etc.) and alert on any container leaving `healthy`.
- **API logs**: `docker compose logs api` — set the host logging driver
  to `json-file` with rotation, or forward to a log aggregator (Loki,
  CloudWatch, etc.).
- **Postgres**: enable `pg_stat_statements`; export metrics with
  `postgres_exporter` if you run Prometheus.
- **Redis**: alert when `connected_clients` drops to zero while the API
  is running (indicates the realtime broker is disconnected).
- **WebSocket**: count `presence.joined` events per minute and alert on
  sustained zero traffic during business hours.

Application errors surface as 5xx responses in API access logs; tail
those during a deploy:

```bash
docker compose --profile app logs -f --tail=200 api proxy
```

## Rate Limits

Set `RATE_LIMIT_ENABLED=true` in production. The default buckets are:

| Bucket     | Limit    | Window | Key             |
| ---------- | -------- | ------ | --------------- |
| `auth`     | 30 req   | 60 s   | client IP       |
| `upload`   | 10 req   | 60 s   | user id or IP   |
| `mutation` | 240 req  | 60 s   | user id or IP   |

When `REDIS_URL` is set, counters are stored in Redis so all `api`
replicas share state; otherwise an in-process fallback keeps the limits
per-replica. A 429 response includes `Retry-After: 60`.

## Incident Response

1. **API hard down**: check `docker compose ps`; restart with
   `docker compose --profile app up -d api`. If Postgres is healthy but
   the API container is crash-looping, inspect `docker compose logs api`
   for tracebacks; the most common causes are missing env vars or a bad
   migration. Roll back the image tag if a recent deploy is implicated.
2. **Sessions invalid for everyone**: someone rotated `JWT_SECRET`
   without coordinating. Users must log in again. Cannot be undone — do
   not roll back the secret to the previous value, that opens a window
   for stolen tokens.
3. **Realtime updates missing**: confirm `REDIS_URL` resolves and Redis
   is healthy. Look for `Failed to dispatch realtime event from Redis`
   in API logs. Fall back to single-replica mode (`api`) if needed; the
   in-memory broker keeps presence and broadcasts working within one
   process while Redis is recovered.
4. **Map image not loading**: presigned URLs expire after the configured
   window. If MinIO is up but uploads 403, verify `S3_PUBLIC_ENDPOINT_URL`
   is reachable from the browser and matches the bucket's CORS rules.
5. **Database degraded**: take a fresh dump first, then investigate. Do
   not run `VACUUM FULL` during traffic — schedule it.

## Release Checklist

Before promoting a build:

- [ ] `docker compose --profile app build` succeeds locally
- [ ] `cd apps/api && python3 -m pytest -q` is green
- [ ] `cd apps/web && npm run typecheck && npm run lint && npm run build` are green
- [ ] `alembic upgrade head` was tested against a production-shaped DB
- [ ] `.env` on the deploy host includes any newly required variables
- [ ] Backup snapshot taken within the last hour
- [ ] `AUTH_ENABLED`, `RATE_LIMIT_ENABLED`, and OAuth credentials match
  production expectations
