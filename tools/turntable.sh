#!/bin/sh
# Turntable (360° orbit) animation for a board, from real KiCad raytraced renders.
#
# Usage:
#   # Single board (host kicad-cli):
#   KICAD_CLI="path/to/kicad-cli" sh tools/turntable.sh boards/ledhub-c6
#
#   # All boards (host kicad-cli):
#   KICAD_CLI="path/to/kicad-cli" sh tools/turntable.sh --all
#
#   # All boards via Docker (no local KiCad install needed):
#   USE_DOCKER=1 sh tools/turntable.sh --all
#
# Renders 24 frames (15° steps) with `kicad-cli pcb render --quality high
# --floor --perspective --rotate "-25,0,<angle>"` and stitches them with
# ffmpeg into:
#   <board>/turntable.gif  — animated GIF (embeds inline on GitHub)
#   <board>/turntable.webm — VP9 WebM (compact, modern browsers)
#   <board>/turntable.mp4  — H.264 MP4 (broad compatibility)
# All three are 8 fps, 3 s seamless loop.
#
# Requirements: ffmpeg; KiCad >= 10.0.0 kicad-cli (or Docker with USE_DOCKER=1).
#   Docker image: kicad/kicad:10.0.0
#   (9.0.9 and 10.0.1 have a regression that drops component 3D models)
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
KICAD_CLI=${KICAD_CLI:-kicad-cli}

_kicad_render() {
    # $1=output $2=angle $3=pcb
    if [ "${USE_DOCKER:-0}" = "1" ]; then
        _tmp_dir="$4"
        docker run --rm \
          --user "$(id -u):$(id -g)" \
          -v "$ROOT:$ROOT" \
          -v "$_tmp_dir:$_tmp_dir" \
          -v "/tmp/kicad-config:/.config" \
          -v "/tmp/kicad-cache:/.cache" \
          -v "/tmp/kicad-local:/.local" \
          kicad/kicad:10.0.0 \
          kicad-cli pcb render -o "$1" -w 960 -h 600 \
            --side top --quality high --floor --perspective --rotate "-25,0,$2" \
            "$3" >/dev/null 2>&1
    else
        "$KICAD_CLI" pcb render -o "$1" -w 960 -h 600 \
          --side top --quality high --floor --perspective --rotate "-25,0,$2" \
          "$3" >/dev/null 2>&1
    fi
}

render_board() {
    d="$1"; b=$(basename "$d")
    tmp=$(mktemp -d)
    i=0
    while [ $i -lt 24 ]; do
        a=$((i * 15))
        _kicad_render "$tmp/f$(printf %03d $i).png" "$a" "$d/$b.kicad_pcb" "$tmp"
        i=$((i + 1))
    done
    # Animated GIF — palettegen pass for quality
    ffmpeg -y -framerate 8 -i "$tmp/f%03d.png" \
        -vf "palettegen=stats_mode=full" "$tmp/palette.png" 2>/dev/null
    ffmpeg -y -framerate 8 -i "$tmp/f%03d.png" -i "$tmp/palette.png" \
        -lavfi "paletteuse=dither=bayer:bayer_scale=5" \
        "$d/turntable.gif" 2>/dev/null
    # WebM (VP9)
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

if [ "${USE_DOCKER:-0}" = "1" ]; then
    mkdir -p /tmp/kicad-config /tmp/kicad-cache /tmp/kicad-local
fi

if [ "$1" = "--all" ]; then
    for pcb in "$ROOT"/boards/*/*.kicad_pcb; do
        render_board "$(dirname "$pcb")"
    done
else
    render_board "$1"
fi
