#!/bin/sh
# Raytraced 3D renders for every board using the official KiCad CLI.
#
# Requirements: KiCad >= 9.0 with `kicad-cli pcb render` (10.0.5 known-good).
#   No X server needed — the raytracer is CPU-based.
#   macOS: the app bundle's kicad-cli is picked up automatically.
#
# 3D models must already be attached (python3 tools/attach_3d.py); footprints
# reference them via ${KIPRJMOD}/../../3dmodels/...
#
# Usage: sh tools/render3d.sh [--force]      (KICAD_CLI=... to override)
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
. "$ROOT/tools/kicad_cli.sh"
for pcb in "$ROOT"/boards/*/*.kicad_pcb; do
    b=$(basename "$pcb" .kicad_pcb); d=$(dirname "$pcb")
    [ -f "$d/render3d_top.png" ] && [ "$1" != "--force" ] && continue
    "$KICAD_CLI" pcb render -o "$d/render3d_top.png" -w 1400 -h 900 \
        --side top --quality high --floor --perspective --rotate '-25,0,20' "$pcb"
    "$KICAD_CLI" pcb render -o "$d/render3d_bottom.png" -w 1400 -h 900 \
        --side bottom --quality high --floor --perspective --rotate '-25,0,-20' "$pcb"
    echo "rendered $b"
done
