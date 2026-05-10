# Hosted Mode Roadmap

This roadmap tracks the gap between the current local-first map editor and a complete hosted campaign map product.

## Milestone 1: Baseline Contracts

1. Freeze the current API resource shapes for campaigns, maps, layers, objects, exports, health checks, and WebSocket map events.
2. Add smoke coverage for the web editor save/export flows and API route contracts.
3. Document the hosted environment matrix for local, CI, staging, and production.

Done when the current in-memory behavior is fully testable and documented as the baseline.

## Milestone 2: Durable Persistence

1. Add Postgres models and migrations for users, OAuth identities, campaigns, maps, layers, objects, memberships, export jobs, and audit timestamps.
2. Implement a Postgres-backed repository while keeping the in-memory adapter for tests.
3. Add seed/reset commands for local development and CI.

Done when restarting the API no longer loses campaign data.

## Milestone 3: Asset Storage

1. Add S3-compatible upload and download flows for map images and generated exports.
2. Use MinIO locally and a managed S3-compatible bucket in hosted environments.
3. Store object keys and metadata in Postgres, not raw image payloads.

Done when uploaded map images and generated exports survive app restarts and deploys.

## Milestone 4: Auth and Permissions

1. Add OAuth login for Discord, Google, and GitHub.
2. Store OAuth identities and sessions securely, with HTTP-only cookies and CSRF protection.
3. Enforce campaign roles: owner, GM, player, and viewer.

Done when private campaigns are only visible and editable by authorized users.

## Milestone 5: Realtime and Jobs

1. Move WebSocket fanout and presence coordination onto Redis.
2. Add Redis-backed queues or worker coordination for export generation and future import tasks.
3. Add rate limits for auth, uploads, and mutation-heavy endpoints.

Done when realtime updates and export jobs work reliably across more than one API process.

## Milestone 6: Hosted Operations

1. Add deployment smoke tests, migration runbooks, backup restore checks, and release rollback notes.
2. Add observability for API errors, latency, worker jobs, storage usage, and WebSocket connection counts.
3. Harden container images, secret rotation, TLS, CORS/CSRF origins, and public bucket access rules.

Done when the stack can be promoted to a maintained hosted environment with clear operating procedures.
