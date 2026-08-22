#!/bin/sh
# Turntable (360° orbit) GIF for a board, from real KiCad raytraced renders.
#
#   sh tools/turntable.sh boards/ledhub-c6       (KICAD_CLI=... to override)
#   sh tools/turntable.sh                        # every board without a GIF
#
# Renders 24 frames (15° steps) with `kicad-cli pcb render --quality high
# --floor --perspective --zoom 0.75 --rotate "-25,0,<angle>"` and stitches them with
# ffmpeg (two-pass palette) into <board>/turntable.gif: 8 fps, 3 s loop.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
. "$ROOT/tools/kicad_cli.sh"
one() {
    d="$1"; b=$(basename "$d")
    tmp=$(mktemp -d)
    i=0
    while [ $i -lt 24 ]; do
        "$KICAD_CLI" pcb render -o "$tmp/f$(printf %03d $i).png" -w 800 -h 500 \
            --side top --quality high --floor --perspective --zoom 0.75 \
            --rotate "-25,0,$((i * 15))" "$d/$b.kicad_pcb" >/dev/null 2>&1
        i=$((i + 1))
    done
    ffmpeg -loglevel error -y -framerate 8 -i "$tmp/f%03d.png" \
        -vf 'split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle' \
        -loop 0 "$d/turntable.gif"
    rm -rf "$tmp"
    echo "wrote $d/turntable.gif"
}
if [ -n "$1" ]; then
    one "$1"
else
    for d in "$ROOT"/boards/*/; do
        d=${d%/}
        [ -f "$d/$(basename "$d").kicad_pcb" ] || continue
        [ -f "$d/turntable.gif" ] || one "$d"
    done
fi
