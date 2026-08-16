# Documentation standard

Every board in this repo must ship with documentation sufficient to build,
program, and debug it without guessing. For **SMD boards** two things are
non-negotiable and enforced in CI:

## 1. Datasheets (`docs/datasheets/`)

Each board keeps a datasheet index at `boards/<board>/docs/DATASHEETS.md`
(see `docs/datasheets/DATASHEETS-TEMPLATE.md`). It lists every component on
the board — at minimum every IC, module, sensor, connector, and any passive
whose value/tolerance matters — with a link to the manufacturer datasheet.

Download the actual PDFs locally with:

```sh
python3 tools/fetch_datasheets.py            # download all
python3 tools/fetch_datasheets.py --check    # CI lint: index present, no TBD links
```

PDFs land in `boards/<board>/docs/datasheets/` and are git-ignored by default
(manufacturer PDFs are copyrighted; commit them only if you have redistribution
rights — flip `docs/datasheets/.gitignore` if you choose to).

## 2. 3D models + 3D render (`3d/`)

Every SMD footprint must have a 3D model assigned in KiCad, and each board
gets rendered views + a STEP export:

```sh
python3 tools/render_3d.py                 # render all boards
python3 tools/render_3d.py --check-models  # CI lint: footprints missing 3D models
```

Outputs:
- `3d/renders/<board>/top.png`, `bottom.png`, `iso.png`
- `3d/models/<board>.step`

Renders are produced with `kicad-cli` (KiCad 8). Missing 3D models fail CI.

## Release checklist

Before tagging a board release, walk `docs/checklists/smd-board-release.md`.
