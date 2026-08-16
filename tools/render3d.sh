#!/bin/sh
# Raytraced 3D renders for every board using the official KiCad CLI.
#
# Requirements: KiCad >= 9.0 with `kicad-cli pcb render`.
#   Known-good: 10.0.0 AppImage (9.0.9 and 10.0.1 have a regression that
#   drops component 3D models from CLI renders).
#   AppImage: https://www.kicad.org/download/linux/ (previous releases dir).
#   No X server needed — the raytracer is CPU-based.
#
# 3D models must already be fetched (tools/fetch_3d.py + tools/fix_3d.py);
# footprints reference them via ${KIPRJMOD}/../../3dmodels/...
#
# Usage: KICAD_CLI="path/to/kicad-cli" sh tools/render3d.sh
set -e
KICAD_CLI=${KICAD_CLI:-kicad-cli}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
for pcb in "$ROOT"/boards/*/*.kicad_pcb; do
    b=$(basename "$pcb" .kicad_pcb); d=$(dirname "$pcb")
    [ -f "$d/render3d_top.png" ] && [ "$1" != "--force" ] && continue
    "$KICAD_CLI" pcb render -o "$d/render3d_top.png" -w 1400 -h 900 \
        --side top --quality high --floor --perspective --rotate '-25,0,20' "$pcb"
    "$KICAD_CLI" pcb render -o "$d/render3d_bottom.png" -w 1400 -h 900 \
        --side bottom --quality high --floor --perspective --rotate '-25,0,-20' "$pcb"
    echo "rendered $b"
done
