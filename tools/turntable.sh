#!/bin/sh
# Turntable (360° orbit) animation for a board, from real KiCad raytraced renders.
#
#   KICAD_CLI="path/to/kicad-cli" sh tools/turntable.sh boards/ledhub-c6
#   # or for all boards:
#   KICAD_CLI="path/to/kicad-cli" sh tools/turntable.sh --all
#
# Renders 24 frames (15° steps) with `kicad-cli pcb render --quality high
# --floor --perspective --rotate "-25,0,<angle>"` and stitches them with
# ffmpeg into:
#   <board>/turntable.gif  — animated GIF (embeds inline on GitHub)
#   <board>/turntable.webm — VP9 WebM (compact, modern browsers)
#   <board>/turntable.mp4  — H.264 MP4 (broad compatibility)
# All three are 8 fps, 3 s seamless loop.
set -e
KICAD_CLI=${KICAD_CLI:-kicad-cli}
ROOT=$(cd "$(dirname "$0")/.." && pwd)

render_board() {
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
    # Animated GIF — palettegen pass for quality
    ffmpeg -y -framerate 8 -i "$tmp/f%03d.png" \
        -vf "palettegen=stats_mode=full" "$tmp/palette.png" 2>/dev/null
    ffmpeg -y -framerate 8 -i "$tmp/f%03d.png" -i "$tmp/palette.png" \
        -lavfi "paletteuse=dither=bayer:bayer_scale=5" \
        "$d/turntable.gif" 2>/dev/null
    # WebM (VP9, lossless-ish quality)
    ffmpeg -y -framerate 8 -i "$tmp/f%03d.png" \
        -c:v libvpx-vp9 -crf 30 -b:v 0 -loop 0 \
        "$d/turntable.webm" 2>/dev/null
    # MP4 (H.264 fallback)
    ffmpeg -y -framerate 8 -i "$tmp/f%03d.png" \
        -vf format=yuv420p -c:v libx264 -crf 20 -movflags +faststart \
        "$d/turntable.mp4" 2>/dev/null
    rm -rf "$tmp"
    echo "wrote $b turntable.{gif,webm,mp4}"
}

if [ "$1" = "--all" ]; then
    for pcb in "$ROOT"/boards/*/*.kicad_pcb; do
        render_board "$(dirname "$pcb")"
    done
else
    render_board "$1"
fi
