# Sourced by the render scripts: resolve $KICAD_CLI (env override, PATH, or
# the macOS app bundle) and fail loudly if none works.
if [ -z "$KICAD_CLI" ]; then
    if command -v kicad-cli >/dev/null 2>&1; then
        KICAD_CLI=kicad-cli
    elif [ -x /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli ]; then
        KICAD_CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
    else
        echo "kicad-cli not found: install KiCad >= 9 or set KICAD_CLI" >&2
        exit 1
    fi
fi
