#!/usr/bin/env python3
"""Fetch and lint per-board component datasheets.

Each board under boards/ must contain docs/DATASHEETS.md — a markdown table
with a 'Datasheet URL' column. This tool can:

  --check   lint only (CI): index exists per board, no TBD/empty URLs.
            Exit 1 on failure.
  (default) download every datasheet PDF into boards/<board>/docs/datasheets/

A missing DATASHEETS.md is always an error.
"""

import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARDS = ROOT / "boards"
URL_RE = re.compile(r"^https?://", re.I)


def find_indexes() -> list[Path]:
    if not BOARDS.is_dir():
        return []
    return sorted(BOARDS.glob("*/docs/DATASHEETS.md"))


def missing_indexes() -> list[Path]:
    if not BOARDS.is_dir():
        return []
    boards = [d for d in BOARDS.iterdir() if d.is_dir()]
    return [d for d in sorted(boards) if not (d / "docs" / "DATASHEETS.md").is_file()]


def parse_urls(index: Path) -> list[tuple[str, str]]:
    """Return (designator, url) pairs from the markdown table."""
    rows = []
    for line in index.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|") or "---" in line or "Datasheet URL" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        rows.append((cells[0], cells[3]))
    return rows


def lint() -> int:
    ok = True
    for board in missing_indexes():
        print(f"FAIL  {board.name}: missing docs/DATASHEETS.md")
        ok = False
    for index in find_indexes():
        for ref, url in parse_urls(index):
            if not url or url.upper() == "TBD":
                print(f"FAIL  {index.parent.parent.name}: {ref} has no datasheet URL")
                ok = False
            elif not URL_RE.match(url):
                print(f"FAIL  {index.parent.parent.name}: {ref} URL is not http(s): {url}")
                ok = False
    if not find_indexes() and not missing_indexes():
        print("No boards found under boards/ — nothing to check.")
    return 0 if ok else 1


def fetch() -> int:
    rc = 0
    for index in find_indexes():
        board = index.parent.parent.name
        out_dir = index.parent / "datasheets"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / ".gitkeep").touch(exist_ok=True)
        for ref, url in parse_urls(index):
            if not URL_RE.match(url):
                print(f"SKIP  {board}/{ref}: {url!r}")
                rc = 1
                continue
            name = url.rstrip("/").rsplit("/", 1)[-1] or "datasheet.pdf"
            if "." not in name[-6:]:
                name += ".pdf"
            dest = out_dir / name
            try:
                print(f"GET   {board}/{ref} -> {dest.relative_to(ROOT)}")
                urllib.request.urlretrieve(url, dest)
            except Exception as e:  # noqa: BLE001
                print(f"FAIL  {board}/{ref}: {e}")
                rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(lint() if "--check" in sys.argv else fetch())
