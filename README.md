# D&D Campaign Map

A minimal, stateless browser tool for editing D&D maps.

The app is now just a Next.js frontend. It loads images locally in the browser, lets you add and edit map notes, and exports PNG/PDF files client-side. There is no backend, auth, hosted campaign shell, database, Docker stack, or external object storage.

## Current Features

- Browser-only map editor with image loading, pan/zoom, markers, labels, routes, and freehand trails.
- DM/player visibility controls for map notes.
- Client-side PNG and PDF export of the current view, plus full-map PNG export.

## Run Locally

```powershell
cd apps/web
npm install
npm run dev
```

Open `http://localhost:3000`.

## Checks

```powershell
cd apps/web
npm run typecheck
npm run lint
```

## Layout

```text
apps/web/
  app/                 # Next.js app shell
  components/MapEditor.tsx
  lib/api.ts           # shared editor types only
  lib/pdfExport.ts     # browser-side PDF export helper
```
