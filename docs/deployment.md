# Self-Hosted Deployment

Step-by-step guide for getting Campaign Map Forge running on a Linux server.
For ongoing operations (backups, secret rotation, observability, incident response) see [operations.md](./operations.md).

---

## Prerequisites

**Server**
- Linux host — Ubuntu 22.04+ or Debian 12+ recommended
- 1 GB RAM minimum, 2 GB+ recommended (API + web + Postgres + Redis + MinIO all run together)
- 5 GB disk minimum, more if you expect many map image uploads

**Software on the server**
- Docker Engine 24+ with Compose v2 (`docker compose version`)
- Git
- `openssl` (ships with every major distro; used to generate secrets)

**Networking**
- Outbound internet access to pull container images during the first build
- Firewall: keep ports 5432 (Postgres), 6379 (Redis), 8000 (API), 9000/9001 (MinIO) closed to the public internet — only port 8080 (the nginx proxy) needs to be reachable, or port 443 if you put a TLS terminator in front

**Domain (optional but required for TLS and OAuth)**
- A DNS A record pointing your domain at the server's IP

---

## Step 1 — Clone the repository

```bash
git clone https://github.com/JaakkoLipp/dndmap.git
cd dndmap
```

---

## Step 2 — Configure the environment

### 2a. Copy the template

```bash
cp .env.example .env
```

### 2b. Generate secrets

Run this command four times, once for each secret below, and copy each output:

```bash
openssl rand -base64 48
```

Open `.env` and fill in these values:

| Variable | What to put |
|---|---|
| `POSTGRES_PASSWORD` | First generated value |
| `REDIS_PASSWORD` | Second generated value |
| `JWT_SECRET` | Third generated value |
| `SESSION_SECRET` | Fourth generated value |

> `JWT_SECRET` signs session tokens. `SESSION_SECRET` signs OAuth state parameters.
> Both must be at least 32 characters. Keep them out of version control.

### 2c. Set the database password consistently

`POSTGRES_PASSWORD` and `DATABASE_URL` are independent variables — update both:

```dotenv
POSTGRES_PASSWORD=your_generated_password

DATABASE_URL=postgresql+asyncpg://dndmap:your_generated_password@postgres:5432/dndmap
```

Substitute the same password in both places.

### 2d. Enable authentication and Postgres persistence

The defaults ship with auth off and in-memory storage (data lost on restart). For a real deployment, set:

```dotenv
# Use Postgres for durable storage
PERSISTENCE_BACKEND=postgres

# Enable login
AUTH_ENABLED=true
```

### 2e. Set public URLs

For **local or LAN access** (HTTP on port 8080), the defaults work — skip this section.

For a **public domain** (with or without TLS), set your domain everywhere:

```dotenv
PUBLIC_SITE_URL=https://maps.example.com
CSRF_TRUSTED_ORIGINS=https://maps.example.com
OAUTH_REDIRECT_BASE_URL=https://maps.example.com/api/v1/auth
```

Replace `maps.example.com` with your actual domain throughout.

> `NEXT_PUBLIC_API_BASE_URL` does **not** need to be changed. The web app makes
> API calls as relative paths (`/api/v1/...`) which the nginx proxy routes
> correctly on any domain.

### 2f. Minimum working .env summary

```dotenv
PERSISTENCE_BACKEND=postgres
AUTH_ENABLED=true

POSTGRES_PASSWORD=<generated>
DATABASE_URL=postgresql+asyncpg://dndmap:<generated>@postgres:5432/dndmap

REDIS_PASSWORD=<generated>
REDIS_URL=redis://:<generated>@redis:6379/0

JWT_SECRET=<generated>
SESSION_SECRET=<generated>
```

Everything else in `.env.example` can stay at its default for now.

---

## Step 3 — Build and start the stack

```bash
docker compose --profile app up -d --build
```

This builds the API and web containers then starts all six services:
`postgres`, `redis`, `minio`, `minio-create-bucket` (one-shot bucket init), `api`, `web`, and `proxy`.

Wait for everything to come up:

```bash
docker compose ps
```

All long-running services should show `healthy` or `running`. The `minio-create-bucket` job will show `exited (0)` — that is correct.

If something is unhealthy:

```bash
docker compose logs api       # most common place for startup errors
docker compose logs postgres
```

---

## Step 4 — Run database migrations

```bash
docker compose exec api dndmap-db migrate
```

Expected output: `Migrations complete`

Verify the migration head:

```bash
docker compose exec api alembic current
```

---

## Step 5 — Verify the installation

Open `http://localhost:8080` (or your domain) in a browser. You should be redirected to `/login`.

**Username login smoke test:**

1. Enter any username (e.g. `TestDM`) and click **Continue**.
2. A new account is created automatically on first login.
3. You land on the campaigns list.
4. Create a campaign, create a map, open the map editor.
5. Open an incognito window, log in as `TestPlayer`, accept a campaign invite link.
6. Both users can now see the same campaign.
7. Click **Sign out** — you are redirected to `/login`.

If login returns a 503 error, check:
- `AUTH_ENABLED=true` is in your `.env`
- `JWT_SECRET` is set and at least 32 characters
- The API container restarted after you updated `.env` (`docker compose restart api`)

---

## Optional: TLS with Caddy

Caddy is the simplest way to get automatic HTTPS via Let's Encrypt. Install it on the same host, point it at port 8080, and it handles certificate issuance and renewal.

### Install Caddy (Debian/Ubuntu)

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

### Configure Caddy

Edit `/etc/caddy/Caddyfile`:

```caddyfile
maps.example.com {
    encode zstd gzip

    reverse_proxy localhost:8080 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

Apply the config:

```bash
sudo systemctl reload caddy
```

Caddy will obtain and install a certificate on the first request. Check `sudo journalctl -u caddy -f` if the certificate request fails.

### Update .env for HTTPS

```dotenv
APP_ENV=production
PUBLIC_SITE_URL=https://maps.example.com
CSRF_TRUSTED_ORIGINS=https://maps.example.com
OAUTH_REDIRECT_BASE_URL=https://maps.example.com/api/v1/auth
```

`APP_ENV=production` marks the auth cookie `Secure`, which is required for HTTPS-only cookies.

Restart the API to apply:

```bash
docker compose restart api
```

### Traefik alternative (Compose labels)

Add these labels to the `proxy` service in `docker-compose.yml`:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.dndmap.rule=Host(`maps.example.com`)"
  - "traefik.http.routers.dndmap.entrypoints=websecure"
  - "traefik.http.routers.dndmap.tls.certresolver=letsencrypt"
  - "traefik.http.services.dndmap.loadbalancer.server.port=80"
```

Consult the Traefik documentation for the certificate resolver configuration.

---

## Optional: OAuth login

Username login is fully functional without OAuth. OAuth lets users sign in with an existing Discord, Google, or GitHub account. You can enable any combination.

OAuth requires HTTPS — providers will reject `http://` callback URLs.

### Discord

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications) → New Application.
2. Under **OAuth2 → Redirects**, add:
   ```
   https://maps.example.com/api/v1/auth/discord/callback
   ```
3. Copy the Client ID and Client Secret into `.env`:
   ```dotenv
   OAUTH_DISCORD_CLIENT_ID=your_client_id
   OAUTH_DISCORD_CLIENT_SECRET=your_client_secret
   ```

### Google

1. Open [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials → Create OAuth 2.0 Client ID.
2. Application type: **Web application**.
3. Add Authorized redirect URI:
   ```
   https://maps.example.com/api/v1/auth/google/callback
   ```
4. Copy credentials into `.env`:
   ```dotenv
   OAUTH_GOOGLE_CLIENT_ID=your_client_id
   OAUTH_GOOGLE_CLIENT_SECRET=your_client_secret
   ```

### GitHub

1. Go to GitHub → Settings → Developer settings → OAuth Apps → New OAuth App.
2. Set **Authorization callback URL** to:
   ```
   https://maps.example.com/api/v1/auth/github/callback
   ```
3. Copy credentials into `.env`:
   ```dotenv
   OAUTH_GITHUB_CLIENT_ID=your_client_id
   OAUTH_GITHUB_CLIENT_SECRET=your_client_secret
   ```

### Apply provider credentials

```bash
docker compose restart api
```

Test each provider by clicking its button on the login page. A redirect to `/login?error=provider_not_configured` means the credentials are missing or mis-copied.

---

## Optional: External S3 for map images

By default map image uploads go into the local MinIO container. For a more durable setup, swap MinIO for a real S3-compatible bucket.

```dotenv
S3_BUCKET=your-bucket-name
S3_REGION=us-east-1
S3_ACCESS_KEY_ID=your_key_id
S3_SECRET_ACCESS_KEY=your_secret_key

# AWS S3 — leave S3_ENDPOINT_URL unset (or empty)
S3_ENDPOINT_URL=
S3_PUBLIC_ENDPOINT_URL=https://your-bucket.s3.amazonaws.com
S3_FORCE_PATH_STYLE=false

# Cloudflare R2 or other S3-compatible service
# S3_ENDPOINT_URL=https://your-account.r2.cloudflarestorage.com
# S3_FORCE_PATH_STYLE=true
```

Then restart the API:

```bash
docker compose restart api
```

If you keep the default MinIO container, back up its data volume (`minio-data`) regularly — see [operations.md](./operations.md).

---

## Upgrading

1. Pull the latest code:
   ```bash
   git pull
   ```

2. Check `.env.example` for new variables and add any missing ones to your `.env`.

3. Rebuild and restart:
   ```bash
   docker compose --profile app up -d --build
   ```

4. Run migrations:
   ```bash
   docker compose exec api dndmap-db migrate
   ```

5. Confirm everything is healthy:
   ```bash
   docker compose ps
   docker compose logs --tail=50 api
   ```

---

## Resetting data

Stop containers, keep volumes:

```bash
docker compose down
```

Wipe all data (Postgres, Redis, MinIO) — this is irreversible:

```bash
docker compose down -v
```

After a full wipe, bring the stack back up and re-run migrations:

```bash
docker compose --profile app up -d --build
docker compose exec api dndmap-db migrate
```

To seed the database with one development user, campaign, and map:

```bash
docker compose exec api dndmap-db seed
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Login returns 503 "AUTH_ENABLED is not set" | `AUTH_ENABLED=false` in `.env` | Set `AUTH_ENABLED=true`, restart `api` |
| Login returns 503 "JWT_SECRET is not configured" | `JWT_SECRET` missing or empty | Generate with `openssl rand -base64 48`, restart `api` |
| API container keeps restarting | Bad `DATABASE_URL` or missing env var | `docker compose logs api` — look for the traceback |
| Postgres unhealthy | Wrong password in `DATABASE_URL` vs `POSTGRES_PASSWORD` | Make sure both use the same password value |
| Map images return 403 or fail to load | MinIO not healthy, or wrong public endpoint | Check `docker compose ps minio`; verify `S3_PUBLIC_ENDPOINT_URL` is reachable from the browser |
| OAuth redirects to `/login?error=provider_not_configured` | Client ID or secret missing for that provider | Add credentials to `.env`, run `docker compose restart api` |
| OAuth redirects to `/login?error=session_secret_missing` | `SESSION_SECRET` not set | Generate with `openssl rand -base64 48`, restart `api` |
| OAuth redirects to `/login?error=invalid_state` | State token expired or tampered | User should retry; not actionable unless it's persistent |
| Auth cookie not set after login (HTTP) | `APP_ENV=production` marks cookie `Secure`, won't send over HTTP | Only use `APP_ENV=production` when serving HTTPS |
| Realtime updates not propagating | Redis connection issue | Check `REDIS_URL` and `docker compose ps redis` |
| Build fails: `expected requirements.txt or pyproject.toml` | API directory layout unexpected | Confirm `apps/api/pyproject.toml` exists in the repo |

### Useful diagnostic commands

```bash
# Container status
docker compose ps

# Live API logs
docker compose logs -f api

# Check which migration version is active
docker compose exec api alembic current

# Test the API directly (bypasses the web frontend)
curl -s http://localhost:8000/api/v1/health | jq .

# Check MinIO bucket exists
docker compose exec minio mc ls local/
```

---

For backups, secret rotation, observability setup, and incident response procedures see [operations.md](./operations.md).
