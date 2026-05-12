# AGENTS.md

This repo is a minimal, stateless browser tool for editing D&D maps.

## Ownership

| Path | Description |
|---|---|
| `apps/web/components/MapEditor.tsx` | Main browser-side editor. Keep behavior changes focused and verify editing/export flows. |
| `apps/web/lib/api.ts` | Shared editor types only. Do not reintroduce network API clients here. |
| `apps/web/lib/pdfExport.ts` | Client-side PDF export helper. |
| `apps/web/app/page.tsx` | Loads the editor with `dynamic(..., { ssr: false })`. |
| `apps/web/app/globals.css` | Editor styling. Avoid visual churn unless it is part of the task. |

## Project Rules

- Keep the app stateless and browser-only.
- Do not add auth, accounts, hosted campaign routes, middleware, backend services, Docker compose, databases, object storage, or realtime infrastructure.
- `MapEditor` must remain a client component and should continue to be loaded with `ssr: false`.
- Run frontend checks from `apps/web` with `npm run typecheck` and `npm run lint` after code changes.
