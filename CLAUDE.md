# CLAUDE.md

## Overview

This repository is a web-only D&D map editor. It is intentionally stateless: maps are edited in the browser, images are loaded locally, and PNG/PDF export happens client-side.

There is no backend, auth system, database, Docker compose stack, hosted campaign shell, object storage, or realtime collaboration layer.

## Frontend

- `apps/web/app/page.tsx` loads the editor using `dynamic(..., { ssr: false })`.
- `apps/web/components/MapEditor.tsx` contains the browser-side SVG editor.
- `apps/web/lib/api.ts` contains shared editor types only.
- `apps/web/lib/pdfExport.ts` contains the browser-side PDF export helper.

## Commands

```bash
cd apps/web
npm install
npm run dev
npm run typecheck
npm run lint
```
