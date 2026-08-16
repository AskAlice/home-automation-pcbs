# 3D models & renders

Every SMD board in this repo must include its components' 3D models in a
rendered view of the assembled board.

## Layout

```
3d/
  models/           STEP exports per board  (<board>.step)
  models/lib/       third-party component STEP files referenced by footprints
  renders/<board>/  top.png, bottom.png, iso.png
```

## Regenerating

Requires KiCad 8 (`kicad-cli` on PATH):

```sh
python3 tools/render_3d.py
```

The script scans `boards/*/` for `.kicad_pcb` files and, for each one:

1. renders top, bottom, and 3/4-isometric PNGs,
2. exports a STEP of the populated board,
3. reports any footprint that has no 3D model assigned
   (`--check-models` makes this a hard failure for CI).

## Assigning 3D models in KiCad

- Prefer KiCad 8 bundled `Package_*` / `Connector_*` models.
- For parts KiCad doesn't ship, grab the STEP from the manufacturer, SnapEDA,
  or GrabCAD and put it in `3d/models/lib/<part>.step`, then reference it in
  the footprint's 3D settings with a repo-relative path so it travels with
  the repo.
