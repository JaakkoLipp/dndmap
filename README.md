# D&D Campaign Map

A minimal, stateless browser tool for editing D&D maps.

The app is now just a Next.js frontend. It loads images locally in the browser, lets you add and edit map notes, and exports PNG/PDF files client-side. There is no backend, auth, hosted campaign shell, database, Docker Compose stack, or external object storage.

## Current Features

- Browser-only map editor with image loading, pan/zoom, markers, labels, routes, and freehand trails.
- DM/player visibility controls for map notes.
- Automatic local autosave: the working map is restored in the same browser after a reload. Use **New campaign** to start fresh and clear the saved draft.
- Portable campaign files: save the whole map (title, image, and notes) to a `.json` file and load it back later or on another machine.
- Client-side exports:
  - DM PNG/PDF of the current view and a full-map PNG.
  - Player handout PNG/PDF rendering only the notes you have shared with players — handy for posting in Discord.

## Run Locally

```powershell
cd apps/web
npm install
npm run dev
```

Open `http://localhost:3000`.

## Docker Deployment

Build and run the frontend as a standalone Next.js container:

```powershell
cd apps/web
docker build -t dndmap-web .
docker run --rm -p 3000:3000 dndmap-web
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
  lib/storage.ts       # local autosave + campaign file save/load
```
