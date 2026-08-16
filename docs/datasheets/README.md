# Datasheets

Per-board datasheet indexes live at `boards/<board>/docs/DATASHEETS.md`.
Copy `DATASHEETS-TEMPLATE.md` from this directory to start a new board.

Rules:

1. **Every SMD board must have a `DATASHEETS.md`.** No exceptions — CI fails
   the build if a board directory under `boards/` is missing one.
2. **Every IC/module/sensor row must have a real datasheet URL.** Commodity
   passives (0402/0603 R/C) may share one row per value with the generic
   manufacturer series datasheet. `TBD` URLs fail CI.
3. Prefer the manufacturer's canonical PDF URL over distributor mirrors
   (Digi-Key/Mouser/LCSC pages change; manufacturer doc portals do not).
4. Run `python3 tools/fetch_datasheets.py` to mirror the PDFs into
   `boards/<board>/docs/datasheets/` for offline reference.
