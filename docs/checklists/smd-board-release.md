# SMD board release checklist

- [ ] `boards/<board>/docs/DATASHEETS.md` exists, follows the template, zero `TBD` URLs
- [ ] `python3 tools/fetch_datasheets.py` downloads every sheet without 404s
- [ ] Every SMD footprint has a 3D model assigned (`python3 tools/render_3d.py --check-models`)
- [ ] `3d/renders/<board>/top.png`, `bottom.png`, `iso.png` committed
- [ ] `3d/models/<board>.step` regenerated from the final layout
- [ ] Schematic PDF + interactive BOM (iBOM) in `boards/<board>/docs/`
- [ ] Fab outputs (gerbers, CPL, BOM) in `boards/<board>/fab/`
- [ ] Board version + date silkscreen matches the git tag
