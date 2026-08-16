#!/usr/bin/env python3
"""Render 3D views and STEP exports for every board, using kicad-cli.

Scans boards/*/ for .kicad_pcb files. For each board:
  - renders top.png, bottom.png, iso.png into 3d/renders/<board>/
  - exports <board>.step into 3d/models/

  --check-models  only verify that every footprint has a 3D model assigned
                  (CI lint, no kicad-cli required). Exit 1 if any missing.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def find_boards() -> list[Path]:
    boards_dir = ROOT / "boards"
    if not boards_dir.is_dir():
        return []
    return sorted(boards_dir.glob("*/*.kicad_pcb"))


def footprints_missing_models(pcb: Path) -> list[str]:
    """Footprints in the .kicad_pcb that have no (model ...) entry."""
    text = pcb.read_text(encoding="utf-8", errors="replace")
    missing = []
    for m in re.finditer(r"\(footprint\s+\"([^\"]+)\"", text):
        j = m.start()
        depth, k = 0, j
        while k < len(text):
            if text[k] == "(":
                depth += 1
            elif text[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        block = text[j : k + 1]
        if "(model" not in block:
            missing.append(m.group(1))
    return missing


def check_models() -> int:
    ok = True
    boards = find_boards()
    if not boards:
        print("No boards found under boards/ — nothing to check.")
        return 0
    for pcb in boards:
        missing = footprints_missing_models(pcb)
        for fp in missing:
            print(f"FAIL  {pcb.parent.name}: footprint {fp} has no 3D model")
            ok = False
        if not missing:
            print(f"OK    {pcb.parent.name}: all footprints have 3D models")
    return 0 if ok else 1


def render() -> int:
    if not shutil.which("kicad-cli"):
        print("kicad-cli not found on PATH (need KiCad 8).", file=sys.stderr)
        return 1
    boards = find_boards()
    if not boards:
        print("No boards found under boards/ — nothing to render.")
        return 0
    if check_models() != 0:
        print("Refusing to render: assign 3D models first.", file=sys.stderr)
        return 1
    rc = 0
    for pcb in boards:
        name = pcb.parent.name
        renders = ROOT / "3d" / "renders" / name
        renders.mkdir(parents=True, exist_ok=True)
        (ROOT / "3d" / "models").mkdir(parents=True, exist_ok=True)
        jobs = [
            (["pcb", "render", "--side", "top", "--quality", "high",
              "--output", str(renders / "top.png"), str(pcb)], "top render"),
            (["pcb", "render", "--side", "bottom", "--quality", "high",
              "--output", str(renders / "bottom.png"), str(pcb)], "bottom render"),
            (["pcb", "render", "--quality", "high", "--perspective",
              "--rotate", "-30,0,45",
              "--output", str(renders / "iso.png"), str(pcb)], "iso render"),
            (["pcb", "export", "step", "--subst-models",
              "--output", str(ROOT / "3d" / "models" / f"{name}.step"), str(pcb)],
             "STEP export"),
        ]
        for args, label in jobs:
            print(f"RUN   {name}: {label}")
            proc = subprocess.run(["kicad-cli", *args], capture_output=True, text=True)
            if proc.returncode != 0:
                print(f"FAIL  {name}: {label}\n{proc.stderr}", file=sys.stderr)
                rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(check_models() if "--check-models" in sys.argv else render())
