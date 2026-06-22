# D&D Campaign Map

A minimal, stateless browser tool for editing D&D maps.

The app is now just a Next.js frontend. It loads images locally in the browser, lets you add and edit map notes, and exports PNG/PDF files client-side. There is no backend, auth, hosted campaign shell, database, Docker Compose stack, or external object storage.

## Current Features

- Browser-only map editor with image loading, pan/zoom, markers, labels, routes, freehand trails, and filled **area/region** polygons.
- DM/player visibility controls for every map note.
- **Player handouts**: attach an image or read-aloud text to any note. Handouts open in a fullscreen card when the note is clicked in Present mode.
- **Present (player view) mode**: a clean, read-only, full-bleed view that shows only the notes you have shared with players — ideal for screen-sharing the map in Discord. Press `Esc` to exit.
- **Fog of war**: hide the unexplored map from players. Draw **Reveal** regions to carve out explored areas, then toggle the fog on; player views and exports show only what has been revealed.
- **Touch friendly**: two-finger pinch to zoom and pan on tablets/touchscreens.
- Automatic local autosave: the working map is restored in the same browser after a reload. Use **New campaign** to start fresh and clear the saved draft.
- Portable campaign files: save the whole map (title, image, and notes) to a `.json` file and load it back later or on another machine.
- Client-side exports:
  - DM PNG/PDF of the current view and a full-map PNG.
  - Player handout PNG/PDF rendering only the notes you have shared with players — handy for posting in Discord.

### Drawing an area or fog reveal

Pick the **Area** tool (decorative region) or the **Reveal** tool (fog-of-war hole), click to drop each vertex, then click the first point again (or press `Enter`) to close it. Press `Esc` to cancel. Any area can be flipped between decorative and reveal from its properties panel, and the **fog** toolbar button toggles the war fog on or off.

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
npm test
```

## Layout

```text
apps/web/
  app/                 # Next.js app shell
  components/MapEditor.tsx
  lib/api.ts           # shared editor types only
  lib/mapObjects.ts    # map-note factories, categories, geometry helpers
  lib/pdfExport.ts     # browser-side PDF export helper
  lib/storage.ts       # local autosave + campaign file save/load
```
