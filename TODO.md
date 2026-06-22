# TODO

The project is intentionally scoped as a stateless browser map editor.

## Editor

- [x] Add polygon / area drawing tool to the toolbar.
- [x] Add handout tool for linked images or text notes (per-note handouts revealed in Present mode).
- [x] Add player-visible export option that renders only shared objects (Player PNG/PDF handout).
- [x] Persist the working map locally so it survives a reload, with portable `.json` campaign save/load.
- [x] Add a Present (player view) mode for screen-sharing only the shared notes.
- [x] Add focused frontend tests for tool selection, object editing, and persistence (Vitest).

- [x] Fog-of-war reveal that masks unexplored regions in Present mode and player exports.
- [x] Touch/gesture support for two-finger pan and pinch zoom on tablets.

## Ideas

- [ ] Soft/blurred fog edges instead of hard polygon cut-outs.
- [ ] Measure tool for distances using a configurable map scale.
