#!/bin/sh
# Turntable (360° orbit) video for a board, from real KiCad raytraced renders.
#
#   KICAD_CLI="path/to/kicad-cli" sh tools/turntable.sh boards/ledhub-c6
#
# Renders 24 frames (15° steps) with `kicad-cli pcb render --quality high
# --floor --perspective --rotate "-25,0,<angle>"` and stitches them with
# ffmpeg into <board>/turntable.mp4 (8 fps, 3 s seamless loop).
set -e
KICAD_CLI=${KICAD_CLI:-kicad-cli}
d="$1"; b=$(basename "$d")
tmp=$(mktemp -d)
i=0
while [ $i -lt 24 ]; do
    a=$((i * 15))
    "$KICAD_CLI" pcb render -o "$tmp/f$(printf %03d $i).png" -w 960 -h 600 \
        --side top --quality high --floor --perspective --rotate "-25,0,$a" \
        "$d/$b.kicad_pcb" >/dev/null 2>&1
    i=$((i + 1))
done
ffmpeg -y -framerate 8 -i "$tmp/f%03d.png" -vf format=yuv420p -c:v libx264 \
    -crf 20 -movflags +faststart "$d/turntable.mp4"
rm -rf "$tmp"
echo "wrote $d/turntable.mp4"
