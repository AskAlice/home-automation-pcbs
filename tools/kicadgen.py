#!/usr/bin/env python3
"""kicadgen - minimal KiCad 8 S-expression writer + project validator.

Shared library for the home-automation-pcbs generators.  Python 3.10+,
standard library only, no KiCad installation required: files are written
as text following the KiCad 8 S-expression formats:

  * symbol library : (kicad_symbol_lib (version 20220914) ...)
  * schematic      : (kicad_sch (version 20230121) ...)
  * pcb            : (kicad_pcb (version 20240108) ...)
  * project        : JSON (.kicad_pro)

API contract (SPEC.md section 3):

    SymbolLib(lib_name)
        .add_box_symbol(name, ref_prefix, pins, footprint="", datasheet="")
        .add_power_symbol(name)
        .save(path)
    Schematic(title, lib)
        .place(sym_name, ref, x, y, rot=0, value=None, footprint=None)
        .place_power(name, x, y, rot=0)
        .wire(points)  .label(name, x, y, rot=0)  .global_label(name, x, y, rot=0)
        .no_connect(x, y)  .text(txt, x, y, size=1.5)  .sheet_note(txt)
        .save(path)
    Footprint(lib_name, name)
        .add_pad(num, kind, shape, x, y, sx, sy, layers=("F.Cu","F.Paste","F.Mask"),
                 drill=None, net=None)
        .add_line(x1, y1, x2, y2, layer="F.Silkscreen", width=0.12)
        .add_rect(x1, y1, x2, y2, layer, width=0.12)
        .add_circle(cx, cy, r, layer="F.Silkscreen", width=0.12)
        .add_text(txt, x, y, layer="F.Silkscreen", size=1.0)
    PCB(title)
        .set_outline(w, h, x0=0, y0=0)  .add_mounting_holes(inset=3.5)
        .add_footprint(fp, ref, value, x, y, rot=0)  .set_pad_net(ref, pad_num, net_name)
        .net(name)  .segment(net, x1, y1, x2, y2, layer="F.Cu", width=0.25)
        .route(net, pts, layer="F.Cu", width=0.25)  .via(net, x, y)
        .gnd_zone(layer="B.Cu")  .keepout_rect(x1, y1, x2, y2, note="")
        .silk_text(txt, x, y, layer="F.Silkscreen", size=1.0)
        .save(path)
    validate_project(board_dir) -> list[str]

Convenience additions (not part of the sacred contract, purely additive):
    Schematic.pin_at(ref, pin_num) -> (x, y)   absolute schematic pin position
    write_project(path, title, lib_name)       minimal valid .kicad_pro
    WHITELIST_FOOTPRINTS                        frozenset of allowed std libs

NOTE: geometry of the built-in whitelisted standard footprints is a close
approximation of the KiCad standard libraries.  Verify against the real
footprint / datasheet before fabrication.
"""

from __future__ import annotations

import json
import math
import re
import uuid as _uuid_mod
from pathlib import Path

# ---------------------------------------------------------------------------
# S-expression rendering / parsing helpers (stdlib only)
# ---------------------------------------------------------------------------


def _fmt(v) -> str:
    """Format a number the way KiCad writes it (no trailing zeros)."""
    if isinstance(v, bool):
        raise TypeError("bool is not a coordinate")
    if isinstance(v, int):
        return str(v)
    f = float(v)
    if f == int(f):
        return str(int(f))
    s = f"{f:.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _q(s) -> str:
    """Quote a string for S-expression output."""
    s = str(s)
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _is_atom(v) -> bool:
    return not isinstance(v, (list, tuple))


def _render(node, indent: int = 0) -> str:
    """Render a nested list as a pretty-printed S-expression."""
    if _is_atom(node):
        return str(node)
    parts = []
    for item in node:
        parts.append(_render(item, indent + 1) if isinstance(item, (list, tuple)) else str(item))
    inline = "(" + " ".join(parts) + ")"
    if len(inline) <= 100 and not any(isinstance(i, (list, tuple)) for i in node[1:]):
        return inline
    pad = "  " * indent
    child_pad = "  " * (indent + 1)
    body = ("\n" + child_pad).join(parts)
    return "(" + body + "\n" + pad + ")"


def _write_sexp(path, root) -> None:
    Path(path).write_text(_render(root) + "\n", encoding="utf-8")


def _uuid() -> str:
    return str(_uuid_mod.uuid4())


class SexpError(ValueError):
    """Raised when a KiCad S-expression file fails to parse."""


def _tokenize(text: str) -> list[str]:
    tokens = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\n\r":
            i += 1
        elif c == "#":  # line comment
            while i < n and text[i] != "\n":
                i += 1
        elif c in "()":
            tokens.append(c)
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while j < n:
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                elif text[j] == '"':
                    break
                else:
                    buf.append(text[j])
                    j += 1
            if j >= n:
                raise SexpError("unterminated string literal")
            tokens.append("".join(buf))
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in " \t\n\r()\"":
                j += 1
            tokens.append(text[i:j])
            i = j
    return tokens


def sexp_parse(text: str) -> list:
    """Parse KiCad S-expression text into nested Python lists."""
    tokens = _tokenize(text)
    pos = 0

    def parse_one():
        nonlocal pos
        if pos >= len(tokens):
            raise SexpError("unexpected end of input")
        tok = tokens[pos]
        if tok == "(":
            pos += 1
            out = []
            while True:
                if pos >= len(tokens):
                    raise SexpError("unbalanced parentheses (missing ')')")
                if tokens[pos] == ")":
                    pos += 1
                    return out
                out.append(parse_one())
        if tok == ")":
            raise SexpError("unbalanced parentheses (unexpected ')')")
        pos += 1
        return tok

    root = parse_one()
    if pos != len(tokens):
        raise SexpError("trailing garbage after root expression")
    if not isinstance(root, list):
        raise SexpError("root is not a list")
    return root


def sexp_parse_file(path) -> list:
    return sexp_parse(Path(path).read_text(encoding="utf-8", errors="replace"))


def find_all(node: list, keyword: str) -> list[list]:
    return [c for c in node if isinstance(c, list) and c and c[0] == keyword]


def find_first(node: list, keyword: str):
    for c in node:
        if isinstance(c, list) and c and c[0] == keyword:
            return c
    return None


def find_deep(node, keyword: str, acc=None) -> list[list]:
    if acc is None:
        acc = []
    if isinstance(node, list):
        if node and node[0] == keyword:
            acc.append(node)
        for c in node:
            find_deep(c, keyword, acc)
    return acc


def get_prop(node: list, name: str):
    for c in node:
        if isinstance(c, list) and len(c) >= 3 and c[0] == "property" and c[1] == name:
            return str(c[2])
    return None


def get_at(node: list):
    at = find_first(node, "at")
    if at and len(at) >= 3:
        x, y = float(at[1]), float(at[2])
        a = float(at[3]) if len(at) > 3 else 0.0
        return (x, y, a)
    return None


# ---------------------------------------------------------------------------
# Coordinate transforms (match kicad-happy analyze_schematic exactly)
# ---------------------------------------------------------------------------

# Decomposed KiCad 6+ schematic symbol transforms (see sch_symbol.cpp).
_ANGLE_TRANSFORM = {
    0: (1, 0, 0, 1),
    90: (0, 1, -1, 0),
    180: (-1, 0, 0, -1),
    270: (0, -1, 1, 0),
}


def _sch_pin_abs(cx: float, cy: float, angle: float, px: float, py: float) -> tuple[float, float]:
    """Absolute schematic position of a symbol pin at local offset (px, py).

    Symbol coordinates are math-up; schematic coordinates are screen-down.
    """
    x1, y1, x2, y2 = _ANGLE_TRANSFORM[int(angle) % 360]
    rpx = x1 * px - y1 * py
    rpy = -x2 * px + y2 * py
    return (round(cx + rpx, 4), round(cy - rpy, 4))


GRID = 1.27  # schematic grid (mm)
PIN_LEN = 2.54
FONT_127 = ["effects", ["font", ["size", "1.27", "1.27"]]]

PIN_TYPES = {
    "input", "output", "bidirectional", "passive",
    "power_in", "power_out", "no_connect",
}

POWER_SYMBOL_NAMES = ("GND", "+3V3", "+5V", "VBUS")


# ---------------------------------------------------------------------------
# Symbol library
# ---------------------------------------------------------------------------


class _SymDef:
    __slots__ = ("name", "ref_prefix", "pins", "graphics", "is_power",
                 "footprint", "datasheet", "description", "lcsc", "mpn")

    def __init__(self, name, ref_prefix, is_power=False):
        self.name = name
        self.ref_prefix = ref_prefix
        self.pins = []          # dicts: number, name, type, x, y, angle
        self.graphics = []      # sexp nodes inside the _0_1 sub-symbol
        self.is_power = is_power
        self.footprint = ""
        self.datasheet = "~"
        self.description = ""
        self.lcsc = ""
        self.mpn = ""


def _pin_node(pin: dict) -> list:
    return [
        "pin", pin["type"], "line",
        ["at", _fmt(pin["x"]), _fmt(pin["y"]), _fmt(pin["angle"])],
        ["length", _fmt(pin["length"])],
        ["name", _q(pin["name"]), FONT_127],
        ["number", _q(pin["number"]), FONT_127],
    ]


def _render_symbol(sym: _SymDef, prefix: str = "") -> list:
    """Render one library symbol.  prefix is 'libname:' when embedded in a
    schematic's lib_symbols section, '' inside the .kicad_sym file."""
    full = prefix + sym.name
    ref_y = -(2 * GRID) if sym.is_power else None
    node = ["symbol", _q(full)]
    if sym.is_power:
        node.append(["power"])
        node.append(["pin_numbers", "hide"])
        node.append(["pin_names", "hide"])
    else:
        node.append(["pin_numbers", ["offset", "1.016"]])
        node.append(["pin_names", ["offset", "1.016"]])
    node += [["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"]]
    ref_effects = ["effects", ["font", ["size", "1.27", "1.27"]]]
    if sym.is_power:
        ref_effects = ["effects", ["font", ["size", "1.27", "1.27"]], ["hide", "yes"]]
    node.append(["property", _q("Reference"), _q(sym.ref_prefix),
                 ["at", "0", _fmt(ref_y if ref_y is not None else -3.81), "0"], ref_effects])
    node.append(["property", _q("Value"), _q(sym.name),
                 ["at", "0", _fmt(3.81 if not sym.is_power else -3.81), "0"], FONT_127])
    hidden = ["effects", ["font", ["size", "1.27", "1.27"]], ["hide", "yes"]]
    node.append(["property", _q("Footprint"), _q(sym.footprint), ["at", "0", "0", "0"], hidden])
    node.append(["property", _q("Datasheet"), _q(sym.datasheet or "~"), ["at", "0", "0", "0"], hidden])
    if sym.lcsc:
        node.append(["property", _q("LCSC"), _q(sym.lcsc), ["at", "0", "0", "0"], hidden])
    if sym.mpn:
        node.append(["property", _q("MPN"), _q(sym.mpn), ["at", "0", "0", "0"], hidden])
    node.append(["property", _q("Description"), _q(sym.description), ["at", "0", "0", "0"], hidden])
    gfx = ["symbol", _q(full + "_0_1")]
    gfx.extend(sym.graphics)
    node.append(gfx)
    pin_unit = ["symbol", _q(full + "_1_1")]
    pin_unit.extend(_pin_node(p) for p in sym.pins)
    node.append(pin_unit)
    return node


class SymbolLib:
    """Project symbol library (<board>-lib.kicad_sym).  Self-contained: every
    schematic symbol is defined here, no external symbol libraries."""

    def __init__(self, lib_name: str):
        self.lib_name = lib_name
        self.symbols: dict[str, _SymDef] = {}

    # -- regular box symbol -------------------------------------------------
    def add_box_symbol(self, name, ref_prefix, pins, footprint="", datasheet="", lcsc="", mpn="") -> None:
        """Add a rectangular symbol.

        pins: list of (number, name, pintype, side) with
        side in {"left", "right", "top", "bottom"}.
        """
        if name in self.symbols:
            raise ValueError(f"duplicate symbol {name!r}")
        sym = _SymDef(name, ref_prefix)
        sym.footprint = footprint
        sym.datasheet = datasheet or "~"
        sym.description = f"{name} ({ref_prefix})"
        sym.lcsc = lcsc or ""
        sym.mpn = mpn or ""

        sides = {"left": [], "right": [], "top": [], "bottom": []}
        for entry in pins:
            num, pname, ptype, side = entry
            if ptype not in PIN_TYPES:
                raise ValueError(f"bad pin type {ptype!r} for {name}:{num}")
            if side not in sides:
                raise ValueError(f"bad pin side {side!r} for {name}:{num}")
            sides[side].append((str(num), str(pname), ptype))

        n_left, n_right = len(sides["left"]), len(sides["right"])
        n_top, n_bot = len(sides["top"]), len(sides["bottom"])
        rows = max(n_left, n_right, 1)
        cols = max(n_top, n_bot)
        body_h = rows * 2.54 + 2.54
        body_w = max(10.16, cols * 2.54 + 2.54)
        hw, hh = body_w / 2, body_h / 2

        for i, (num, pname, ptype) in enumerate(sides["left"]):
            sym.pins.append({"number": num, "name": pname, "type": ptype,
                             "x": -(hw + PIN_LEN), "y": hh - GRID - i * 2.54,
                             "angle": 0, "length": PIN_LEN})
        for i, (num, pname, ptype) in enumerate(sides["right"]):
            sym.pins.append({"number": num, "name": pname, "type": ptype,
                             "x": hw + PIN_LEN, "y": hh - GRID - i * 2.54,
                             "angle": 180, "length": PIN_LEN})
        for i, (num, pname, ptype) in enumerate(sides["top"]):
            x = -((n_top - 1) * 2.54) / 2 + i * 2.54
            sym.pins.append({"number": num, "name": pname, "type": ptype,
                             "x": x, "y": hh + PIN_LEN,
                             "angle": 270, "length": PIN_LEN})
        for i, (num, pname, ptype) in enumerate(sides["bottom"]):
            x = -((n_bot - 1) * 2.54) / 2 + i * 2.54
            sym.pins.append({"number": num, "name": pname, "type": ptype,
                             "x": x, "y": -(hh + PIN_LEN),
                             "angle": 90, "length": PIN_LEN})

        sym.graphics.append([
            "rectangle",
            ["start", _fmt(-hw), _fmt(-hh)],
            ["end", _fmt(hw), _fmt(hh)],
            ["stroke", ["width", "0.254"], ["type", "solid"]],
            ["fill", ["type", "background"]],
        ])
        self.symbols[name] = sym

    # -- power symbol --------------------------------------------------------
    def add_power_symbol(self, name) -> None:
        """Add a power rail symbol (GND, +3V3, +5V, VBUS).

        Contains (power), (pin_numbers hide), (pin_names hide) and exactly
        one power_in pin whose connection point is the symbol origin.
        """
        if name in self.symbols:
            raise ValueError(f"duplicate symbol {name!r}")
        sym = _SymDef(name, "#PWR", is_power=True)
        sym.description = f"Power symbol {name}"
        sym.pins.append({"number": "1", "name": name, "type": "power_in",
                         "x": 0, "y": 0,
                         "angle": 270 if name == "GND" else 90, "length": 0})

        def pl(pts):
            return ["polyline",
                    ["pts"] + [["xy", _fmt(x), _fmt(y)] for x, y in pts],
                    ["stroke", ["width", "0"], ["type", "solid"]],
                    ["fill", ["type", "none"]]]

        if name == "GND":
            # triangle hanging below the origin
            sym.graphics.append(pl([(0, 0), (-1.905, -2.54), (1.905, -2.54), (0, 0)]))
        else:
            # stub going up + horizontal bar (rail style)
            sym.graphics.append(pl([(0, 0), (0, 2.54)]))
            sym.graphics.append(pl([(-1.905, 2.54), (1.905, 2.54)]))
        self.symbols[name] = sym

    # -- output ---------------------------------------------------------------
    def save(self, path) -> None:
        root = ["kicad_symbol_lib",
                ["version", "20220914"],
                ["generator", _q("kicad_symbol_editor")],
                ["generator_version", _q("8.0")]]
        for name in self.symbols:
            root.append(_render_symbol(self.symbols[name]))
        _write_sexp(path, root)


# ---------------------------------------------------------------------------
# Schematic
# ---------------------------------------------------------------------------


class Schematic:
    """Single-sheet .kicad_sch writer with embedded lib_symbols."""

    def __init__(self, title: str, lib: SymbolLib):
        self.title = title
        self.lib = lib
        self.root_uuid = _uuid()
        self._symbols = []      # placed instances
        self._power_count = 0
        self._wires = []        # list of segments ((x1,y1),(x2,y2))
        self._junctions = []    # (x,y)
        self._labels = []       # (name, x, y, rot)
        self._glabels = []      # (name, x, y, rot)
        self._ncs = []          # (x,y)
        self._texts = []        # (txt, x, y, size)
        self._notes = []        # title-block comment lines

    # -- placement ------------------------------------------------------------
    def _symdef(self, sym_name) -> _SymDef:
        try:
            return self.lib.symbols[sym_name]
        except KeyError:
            raise ValueError(f"symbol {sym_name!r} not in library {self.lib.lib_name!r}") from None

    def place(self, sym_name, ref, x, y, rot=0, value=None, footprint=None) -> None:
        if rot % 90:
            raise ValueError("rot must be a multiple of 90")
        sd = self._symdef(sym_name)
        if sd.is_power:
            raise ValueError(f"{sym_name!r} is a power symbol; use place_power()")
        self._symbols.append({
            "def": sd, "ref": str(ref), "x": float(x), "y": float(y), "rot": int(rot),
            "value": str(value) if value is not None else sd.name,
            "footprint": footprint if footprint is not None else sd.footprint,
            "uuid": _uuid(), "pin_uuids": {p["number"]: _uuid() for p in sd.pins},
        })

    def place_power(self, name, x, y, rot=0) -> None:
        if rot % 90:
            raise ValueError("rot must be a multiple of 90")
        sd = self._symdef(name)
        if not sd.is_power:
            raise ValueError(f"{name!r} is not a power symbol; use place()")
        self._power_count += 1
        self._symbols.append({
            "def": sd, "ref": f"#PWR{self._power_count:04d}",
            "x": float(x), "y": float(y), "rot": int(rot),
            "value": name, "footprint": "",
            "uuid": _uuid(), "pin_uuids": {p["number"]: _uuid() for p in sd.pins},
        })

    # -- connectivity -----------------------------------------------------------
    def wire(self, points) -> None:
        """Polyline wire; intermediate points get automatic junctions."""
        pts = [(float(px), float(py)) for px, py in points]
        if len(pts) < 2:
            raise ValueError("wire needs at least 2 points")
        for a, b in zip(pts, pts[1:]):
            if a != b:
                self._wires.append((a, b))
        for p in pts[1:-1]:
            self._junctions.append(p)

    def label(self, name, x, y, rot=0) -> None:
        self._labels.append((str(name), float(x), float(y), int(rot)))

    def global_label(self, name, x, y, rot=0) -> None:
        self._glabels.append((str(name), float(x), float(y), int(rot)))

    def no_connect(self, x, y) -> None:
        self._ncs.append((float(x), float(y)))

    def text(self, txt, x, y, size=1.5) -> None:
        self._texts.append((str(txt), float(x), float(y), float(size)))

    def sheet_note(self, txt) -> None:
        """Add a line to the title-block comment block."""
        self._notes.append(str(txt))

    # -- helpers ----------------------------------------------------------------
    def pin_at(self, ref, pin_num) -> tuple[float, float]:
        """Absolute schematic coordinates of one placed pin."""
        for inst in self._symbols:
            if inst["ref"] == ref:
                for p in inst["def"].pins:
                    if p["number"] == str(pin_num):
                        return _sch_pin_abs(inst["x"], inst["y"], inst["rot"], p["x"], p["y"])
                raise ValueError(f"{ref} has no pin {pin_num!r}")
        raise ValueError(f"no placed symbol with ref {ref!r}")

    def net_names(self) -> set[str]:
        """All named nets declared on this sheet."""
        names = {n for n, *_ in self._labels}
        names |= {n for n, *_ in self._glabels}
        names |= {inst["value"] for inst in self._symbols if inst["def"].is_power}
        return names

    # -- connectivity resolution ---------------------------------------------------
    @staticmethod
    def _on_segment(p, a, b, eps=0.01) -> bool:
        (px, py), (ax, ay), (bx, by) = p, a, b
        if abs((bx - ax) * (py - ay) - (by - ay) * (px - ax)) > eps:
            return False
        return (min(ax, bx) - eps <= px <= max(ax, bx) + eps
                and min(ay, by) - eps <= py <= max(ay, by) + eps)

    def _resolve(self):
        """Union-find connectivity.  Returns (parent, pin_points, problems).

        pin_points: list of (ref, pin_number, point, is_power, power_name).
        """
        parent = {}

        def find(k):
            parent.setdefault(k, k)
            while parent[k] != k:
                parent[k] = parent[parent[k]]
                k = parent[k]
            return k

        def union(a, b):
            parent[find(a)] = find(b)

        for a, b in self._wires:
            union(("pt", a), ("pt", b))
            # junctions/labels/pins lying mid-segment belong to this net too

        pin_points = []
        for inst in self._symbols:
            for p in inst["def"].pins:
                pt = _sch_pin_abs(inst["x"], inst["y"], inst["rot"], p["x"], p["y"])
                pin_points.append((inst["ref"], p["number"], pt,
                                   inst["def"].is_power, inst["value"]))

        attach = [pt for _, _, pt, _, _ in pin_points]
        attach += [(x, y) for _, x, y, _ in self._labels]
        attach += [(x, y) for _, x, y, _ in self._glabels]
        attach += list(self._ncs)
        attach += list(self._junctions)
        for a, b in self._wires:
            for p in attach:
                if self._on_segment(p, a, b):
                    union(("pt", a), ("pt", p))
        # exact-coordinate contact (e.g. power symbol placed on a pin point)
        by_pt: dict[tuple, list] = {}
        for p in attach:
            by_pt.setdefault(p, []).append(p)
        for p, group in by_pt.items():
            if len(group) > 1:
                union(("pt", p), ("pt", group[0]))

        return parent, find, pin_points

    def _check_resolved(self):
        """Assert every symbol pin is wired, labelled or no-connected."""
        parent, find, pin_points = self._resolve()
        wired_roots = set()
        for a, b in self._wires:
            wired_roots.add(find(("pt", a)))
        labelled_points = {(x, y) for _, x, y, _ in self._labels}
        labelled_points |= {(x, y) for _, x, y, _ in self._glabels}
        nc = set(self._ncs)

        problems = []
        for ref, num, pt, is_power, _val in pin_points:
            if pt in nc:
                continue
            if pt in labelled_points:
                continue
            if ("pt", pt) in parent and find(("pt", pt)) in wired_roots:
                continue
            problems.append(f"unresolved pin {ref} pad {num} at ({pt[0]}, {pt[1]})")
        return problems

    # -- output ---------------------------------------------------------------------
    def save(self, path) -> None:
        problems = self._check_resolved()
        if problems:
            raise ValueError("schematic has unresolved pins:\n  " + "\n  ".join(problems))

        used = []
        seen = set()
        for inst in self._symbols:
            nm = inst["def"].name
            if nm not in seen:
                seen.add(nm)
                used.append(nm)

        root = ["kicad_sch",
                ["version", "20230121"],
                ["generator", _q("eeschema")],
                ["generator_version", _q("8.0")],
                ["uuid", _q(self.root_uuid)],
                ["paper", _q("A4")]]

        title_block = ["title_block",
                       ["title", _q(self.title)],
                       ["date", _q("2025-01-01")],
                       ["rev", _q("1.0")]]
        for i, note in enumerate(self._notes, 1):
            title_block.append(["comment", str(i), _q(note)])
        root.append(title_block)

        lib_symbols = ["lib_symbols"]
        for nm in used:
            lib_symbols.append(_render_symbol(self.lib.symbols[nm],
                                              prefix=self.lib.lib_name + ":"))
        root.append(lib_symbols)

        for (x, y) in self._junctions:
            root.append(["junction", ["at", _fmt(x), _fmt(y)],
                         ["diameter", "0"], ["color", "0", "0", "0", "0"],
                         ["uuid", _q(_uuid())]])
        for (x, y) in self._ncs:
            root.append(["no_connect", ["at", _fmt(x), _fmt(y)], ["uuid", _q(_uuid())]])
        for a, b in self._wires:
            root.append(["wire",
                         ["pts", ["xy", _fmt(a[0]), _fmt(a[1])],
                          ["xy", _fmt(b[0]), _fmt(b[1])]],
                         ["stroke", ["width", "0"], ["type", "default"]],
                         ["uuid", _q(_uuid())]])

        def label_effects():
            return ["effects", ["font", ["size", "1.27", "1.27"]],
                    ["justify", "left", "bottom"]]

        for name, x, y, rot in self._labels:
            root.append(["label", _q(name),
                         ["at", _fmt(x), _fmt(y), _fmt(rot)],
                         ["fields_autoplaced", "yes"],
                         label_effects(), ["uuid", _q(_uuid())]])
        for name, x, y, rot in self._glabels:
            root.append(["global_label", _q(name), ["shape", "bidirectional"],
                         ["at", _fmt(x), _fmt(y), _fmt(rot)],
                         ["fields_autoplaced", "yes"],
                         label_effects(), ["uuid", _q(_uuid())],
                         ["property", _q("Intersheetrefs"), _q("${INTERSHEET_REFS}"),
                          ["at", _fmt(x), _fmt(y), "0"],
                          ["effects", ["font", ["size", "1.27", "1.27"]], ["hide", "yes"]]]])
        for txt, x, y, size in self._texts:
            root.append(["text", _q(txt), ["exclude_from_sim", "no"],
                         ["at", _fmt(x), _fmt(y), "0"],
                         ["effects", ["font", ["size", _fmt(size), _fmt(size)]]],
                         ["uuid", _q(_uuid())]])

        for inst in self._symbols:
            sd = inst["def"]
            node = ["symbol",
                    ["lib_id", _q(f"{self.lib.lib_name}:{sd.name}")],
                    ["at", _fmt(inst["x"]), _fmt(inst["y"]), _fmt(inst["rot"])],
                    ["unit", "1"],
                    ["exclude_from_sim", "no"],
                    ["in_bom", "no" if sd.is_power else "yes"],
                    ["on_board", "no" if sd.is_power else "yes"],
                    ["dnp", "no"],
                    ["fields_autoplaced", "yes"],
                    ["uuid", _q(inst["uuid"])]]
            ref_eff = ["effects", ["font", ["size", "1.27", "1.27"]]]
            if sd.is_power:
                ref_eff = ["effects", ["font", ["size", "1.27", "1.27"]], ["hide", "yes"]]
            node.append(["property", _q("Reference"), _q(inst["ref"]),
                         ["at", _fmt(inst["x"]), _fmt(inst["y"] - 5.08), "0"], ref_eff])
            node.append(["property", _q("Value"), _q(inst["value"]),
                         ["at", _fmt(inst["x"]), _fmt(inst["y"] + 5.08), "0"], FONT_127])
            hidden = ["effects", ["font", ["size", "1.27", "1.27"]], ["hide", "yes"]]
            node.append(["property", _q("Footprint"), _q(inst["footprint"]),
                         ["at", _fmt(inst["x"]), _fmt(inst["y"]), "0"], hidden])
            node.append(["property", _q("Datasheet"), _q(sd.datasheet or "~"),
                         ["at", _fmt(inst["x"]), _fmt(inst["y"]), "0"], hidden])
            if sd.lcsc:
                node.append(["property", _q("LCSC"), _q(sd.lcsc),
                             ["at", "0", "0", "0"], hidden])
            if sd.mpn:
                node.append(["property", _q("MPN"), _q(sd.mpn),
                             ["at", "0", "0", "0"], hidden])
            for p in sd.pins:
                node.append(["pin", _q(p["number"]),
                             ["uuid", _q(inst["pin_uuids"][p["number"]])]])
            node.append(["instances",
                         ["project", _q(self.title),
                          ["path", _q("/" + self.root_uuid),
                           ["reference", _q(inst["ref"])], ["unit", "1"]]]])
            root.append(node)

        root.append(["sheet_instances", ["path", _q("/"), ["page", _q("1")]]])
        root.append(["embedded_fonts", "no"])
        _write_sexp(path, root)


# ---------------------------------------------------------------------------
# Footprints
# ---------------------------------------------------------------------------

SILK = "F.SilkS"  # file-format layer name for the F.Silkscreen alias


def _canon_layer(layer: str) -> str:
    """Map friendly layer aliases to canonical KiCad 8 layer names."""
    return {
        "F.Silkscreen": "F.SilkS", "B.Silkscreen": "B.SilkS",
        "F.SilkS": "F.SilkS", "B.SilkS": "B.SilkS",
        "F.Courtyard": "F.CrtYd", "B.Courtyard": "B.CrtYd",
    }.get(layer, layer)


class Footprint:
    """Custom inline footprint builder (emitted inside the .kicad_pcb)."""

    def __init__(self, lib_name: str, name: str):
        self.lib_name = lib_name
        self.name = name
        self.fp_id = f"{lib_name}:{name}"
        self.pads = []      # dicts
        self.graphics = []  # sexp nodes

    # -- pads ----------------------------------------------------------------
    def add_pad(self, num, kind, shape, x, y, sx, sy,
                layers=("F.Cu", "F.Paste", "F.Mask"), drill=None, net=None) -> None:
        if kind not in ("smd", "thru_hole", "np_thru_hole"):
            raise ValueError(f"bad pad kind {kind!r}")
        if shape not in ("circle", "rect", "oval", "roundrect", "trapezoid", "custom"):
            raise ValueError(f"bad pad shape {shape!r}")
        if kind == "smd" and drill is not None:
            raise ValueError("smd pads cannot have a drill")
        self.pads.append({
            "num": str(num), "kind": kind, "shape": shape,
            "x": float(x), "y": float(y), "sx": float(sx), "sy": float(sy),
            "layers": tuple(_canon_layer(l) for l in layers),
            "drill": drill, "net": net,
        })

    # -- graphics ---------------------------------------------------------------
    def add_line(self, x1, y1, x2, y2, layer="F.Silkscreen", width=0.12) -> None:
        self.graphics.append(["fp_line",
                              ["start", _fmt(x1), _fmt(y1)],
                              ["end", _fmt(x2), _fmt(y2)],
                              ["stroke", ["width", _fmt(width)], ["type", "solid"]],
                              ["layer", _q(_canon_layer(layer))],
                              ["uuid", _q(_uuid())]])

    def add_rect(self, x1, y1, x2, y2, layer, width=0.12) -> None:
        self.graphics.append(["fp_rect",
                              ["start", _fmt(x1), _fmt(y1)],
                              ["end", _fmt(x2), _fmt(y2)],
                              ["stroke", ["width", _fmt(width)], ["type", "solid"]],
                              ["fill", "none"],
                              ["layer", _q(_canon_layer(layer))],
                              ["uuid", _q(_uuid())]])

    def add_circle(self, cx, cy, r, layer="F.Silkscreen", width=0.12) -> None:
        self.graphics.append(["fp_circle",
                              ["center", _fmt(cx), _fmt(cy)],
                              ["end", _fmt(cx + r), _fmt(cy)],
                              ["stroke", ["width", _fmt(width)], ["type", "solid"]],
                              ["fill", "none"],
                              ["layer", _q(_canon_layer(layer))],
                              ["uuid", _q(_uuid())]])

    def add_text(self, txt, x, y, layer="F.Silkscreen", size=1.0) -> None:
        self.graphics.append(["fp_text", "user", _q(txt),
                              ["at", _fmt(x), _fmt(y), "0"],
                              ["layer", _q(_canon_layer(layer))],
                              ["uuid", _q(_uuid())],
                              ["effects", ["font", ["size", _fmt(size), _fmt(size)],
                                           ["thickness", _fmt(size * 0.15)]]]])


# --- whitelisted standard-library footprints (SPEC 2.4) ---------------------
# Built-in geometry is a close approximation of the official KiCad libraries;
# board READMEs must carry the "verify before fabrication" note.

def _chip(fp: Footprint, pitch, pw, ph, body_w, body_h):
    """Two-pad SMD chip (resistor/capacitor/LED/fuse)."""
    fp.add_pad("1", "smd", "rect", -pitch / 2, 0, pw, ph)
    fp.add_pad("2", "smd", "rect", pitch / 2, 0, pw, ph)
    hw, hh = body_w / 2, body_h / 2
    fp.add_rect(-hw, -hh, hw, hh, "F.Fab", 0.1)
    cr = hw + 0.25
    fp.add_rect(-cr, -(hh + 0.25), cr, hh + 0.25, "F.CrtYd", 0.05)
    fp.add_line(-hw - 0.2, -hh - 0.1, hw + 0.2, -hh - 0.1, "F.SilkS")
    fp.add_line(-hw - 0.2, hh + 0.1, hw + 0.2, hh + 0.1, "F.SilkS")


def _sot(fp: Footprint, n_left, n_right, pitch=0.95, row_x=0.95):
    """SOT-23 family: pads numbered counter-clockwise from top-left."""
    num = 1
    for i in range(n_left):
        y = -((n_left - 1) * pitch) / 2 + i * pitch
        fp.add_pad(str(num), "smd", "rect", -row_x, y, 0.95, 0.8)
        num += 1
    for i in range(n_right):
        y = ((n_right - 1) * pitch) / 2 - i * pitch
        fp.add_pad(str(num), "smd", "rect", row_x, y, 0.95, 0.8)
        num += 1
    fp.add_rect(-1.5, -0.75, 1.5, 0.75, "F.Fab", 0.1)
    fp.add_rect(-1.7, -1.5, 1.7, 1.5, "F.CrtYd", 0.05)
    fp.add_line(-0.6, -0.85, 0.6, -0.85, "F.SilkS")
    fp.add_line(-0.6, 0.85, 0.6, 0.85, "F.SilkS")


def _pinheader(fp: Footprint, rows, n):
    pitch = 2.54
    num = 1
    xs = [-pitch / 2, pitch / 2] if rows == 2 else [0.0]
    for col, x in enumerate(xs):
        for i in range(n):
            shape = "rect" if num == 1 else "circle"
            fp.add_pad(str(num), "thru_hole", shape, x, i * pitch, 1.7, 1.7,
                       layers=("*.Cu", "*.Mask"), drill=1.0)
            num += 1
    hw = (pitch / 2 + 1.27) if rows == 2 else 1.27
    fp.add_rect(-hw, -1.27, hw, (n - 1) * pitch + 1.27, "F.Fab", 0.1)
    fp.add_rect(-hw - 0.25, -1.52, hw + 0.25, (n - 1) * pitch + 1.52, "F.CrtYd", 0.05)
    fp.add_rect(-hw, -1.27, hw, (n - 1) * pitch + 1.27, "F.SilkS", 0.12)


def _build_std_footprint(fp_id: str) -> Footprint:
    """Instantiate a whitelisted standard-library footprint with built-in
    (approximate) geometry so pads exist for net assignment and routing."""
    lib, name = fp_id.split(":", 1)
    fp = Footprint(lib, name)

    if name in ("R_0603_1608Metric", "C_0603_1608Metric", "LED_0603_1608Metric"):
        _chip(fp, 1.55, 0.85, 0.95, 1.6, 0.8)
    elif name in ("R_0805_2012Metric", "C_0805_2012Metric"):
        _chip(fp, 1.9, 1.0, 1.3, 2.0, 1.25)
    elif name == "Fuse_1206_3216Metric":
        _chip(fp, 2.9, 1.05, 1.85, 3.2, 1.6)
    elif name == "CP_Electrolytic_5x5.3":
        fp.add_pad("1", "smd", "rect", -1.45, 0, 1.5, 2.15)
        fp.add_pad("2", "smd", "rect", 1.45, 0, 1.5, 2.15)
        fp.add_circle(0, 0, 2.5, "F.Fab", 0.1)
        fp.add_circle(0, 0, 2.75, "F.CrtYd", 0.05)
        fp.add_line(-2.5, -2.6, -1.0, -2.6, "F.SilkS")
        fp.add_line(-1.75, -3.0, -1.75, -2.2, "F.SilkS")  # polarity bar
    elif name == "D_SOD-323":
        _chip(fp, 1.95, 0.65, 1.05, 1.7, 1.25)
        fp.add_line(0.35, -0.72, 0.35, 0.72, "F.SilkS", 0.15)  # cathode bar
    elif name == "D_SMA":
        _chip(fp, 4.1, 2.3, 1.9, 4.5, 2.6)
        fp.add_line(1.2, -1.4, 1.2, 1.4, "F.SilkS", 0.15)  # cathode bar
    elif name == "SOT-23":
        _sot(fp, 2, 1)
    elif name == "SOT-23-5":
        _sot(fp, 3, 2)
    elif name == "SOT-23-6":
        _sot(fp, 3, 3)
    elif name == "SOT-223-3_TabPin2":
        for i, num in enumerate(("1", "3", "4")):
            fp.add_pad(num, "smd", "rect", -1.6, 2.3 - i * 2.3, 1.5, 1.0)
        fp.add_pad("2", "smd", "rect", 1.6, 0, 2.2, 3.8)
        fp.add_rect(-1.55, -3.25, 1.55, 3.25, "F.Fab", 0.1)
        fp.add_rect(-2.6, -4.0, 2.9, 4.0, "F.CrtYd", 0.05)
        fp.add_line(-0.8, -3.4, 0.8, -3.4, "F.SilkS")
        fp.add_line(-0.8, 3.4, 0.8, 3.4, "F.SilkS")
    elif name == "SOIC-14_3.9x8.7mm_P1.27mm":
        for i in range(7):
            fp.add_pad(str(i + 1), "smd", "rect", -2.7, -3.81 + i * 1.27, 0.6, 1.5)
            fp.add_pad(str(14 - i), "smd", "rect", 2.7, -3.81 + i * 1.27, 0.6, 1.5)
        fp.add_rect(-1.95, -4.35, 1.95, 4.35, "F.Fab", 0.1)
        fp.add_rect(-3.45, -5.0, 3.45, 5.0, "F.CrtYd", 0.05)
        fp.add_line(-1.95, -4.5, 1.95, -4.5, "F.SilkS")
        fp.add_line(-1.95, 4.5, 1.95, 4.5, "F.SilkS")
        fp.add_circle(-2.7, -4.6, 0.25, "F.SilkS")  # pin-1 dot
    elif name.startswith("PinHeader_1x") and name.endswith("_P2.54mm_Vertical"):
        n = int(name.split("x")[1].split("_")[0])
        if not 1 <= n <= 8:
            raise ValueError(f"pin header size out of range: {fp_id}")
        _pinheader(fp, 1, n)
    elif name == "PinHeader_2x07_P2.54mm_Vertical":
        _pinheader(fp, 2, 7)
    elif name == "USB_C_Receptacle_USB2.0_16P":
        # mid-mount USB-C 2.0 16-pin: 16 SMD pads @0.5 mm pitch + 4 shell THT.
        # Pad order (left->right): 1..16.  Shield pads S1..S4.
        for i in range(16):
            fp.add_pad(str(i + 1), "smd", "rect", -3.75 + i * 0.5, 2.6, 0.3, 1.25)
        for j, (sx, sy) in enumerate(((-4.32, 0.1), (4.32, 0.1), (-4.32, 2.7), (4.32, 2.7))):
            fp.add_pad(f"S{j + 1}", "thru_hole", "circle", sx, sy, 1.1, 1.1,
                       layers=("*.Cu", "*.Mask"), drill=0.6)
        fp.add_rect(-4.45, -1.5, 4.45, 3.4, "F.Fab", 0.1)
        fp.add_rect(-5.6, -2.2, 5.6, 4.4, "F.CrtYd", 0.05)
        fp.add_line(-4.45, -1.6, 4.45, -1.6, "F.SilkS")
    else:  # pragma: no cover - guarded by WHITELIST_FOOTPRINTS
        raise ValueError(f"no built-in geometry for whitelisted footprint {fp_id!r}")
    return fp


def _pinheader_whitelist() -> set:
    return {f"Connector_PinHeader_2.54mm:PinHeader_1x0{n}_P2.54mm_Vertical"
            for n in range(2, 9)}


WHITELIST_FOOTPRINTS = frozenset({
    "Resistor_SMD:R_0603_1608Metric", "Resistor_SMD:R_0805_2012Metric",
    "Capacitor_SMD:C_0603_1608Metric", "Capacitor_SMD:C_0805_2012Metric",
    "Capacitor_SMD:CP_Electrolytic_5x5.3",
    "LED_SMD:LED_0603_1608Metric",
    "Diode_SMD:D_SOD-323", "Diode_SMD:D_SMA",
    "Package_TO_SOT_SMD:SOT-23", "Package_TO_SOT_SMD:SOT-23-5",
    "Package_TO_SOT_SMD:SOT-23-6", "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
    "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    "Connector_PinHeader_2.54mm:PinHeader_2x07_P2.54mm_Vertical",
    "Connector_USB:USB_C_Receptacle_USB2.0_16P",
    "Fuse:Fuse_1206_3216Metric",
} | _pinheader_whitelist())


# ---------------------------------------------------------------------------
# PCB
# ---------------------------------------------------------------------------

# Canonical KiCad 8 two-layer stack (layer numbers as written by pcbnew 8).
# NOTE: SPEC.md 2.3's parenthetical numbers for the user layers do not match
# what KiCad 8 actually writes (e.g. Edge.Cuts is 44 in real files); this
# table follows real KiCad 8 output, which the "canonical KiCad 8 layer list"
# rule intends.
KICAD8_LAYERS = [
    (0, "F.Cu", "signal"),
    (31, "B.Cu", "signal"),
    (32, "B.Adhes", "user", "B.Adhesive"),
    (33, "F.Adhes", "user", "F.Adhesive"),
    (34, "B.Paste", "user"),
    (35, "F.Paste", "user"),
    (36, "B.SilkS", "user"),
    (37, "F.SilkS", "user"),
    (38, "B.Mask", "user"),
    (39, "F.Mask", "user"),
    (40, "Dwgs.User", "user", "User.Drawings"),
    (41, "Cmts.User", "user", "User.Comments"),
    (42, "Eco1.User", "user", "User.Eco1"),
    (43, "Eco2.User", "user", "User.Eco2"),
    (44, "Edge.Cuts", "user"),
    (45, "Margin", "user"),
    (46, "B.CrtYd", "user"),
    (47, "F.CrtYd", "user"),
    (48, "B.Fab", "user"),
    (49, "F.Fab", "user"),
] + [(50 + i, f"User.{i + 1}", "user") for i in range(9)]

COPPER_LAYERS = ("F.Cu", "B.Cu")
POWER_RAIL_MIN_WIDTH = 0.5  # mm, for GND/VBUS/+5V/+3V3/12V rails


class PCB:
    """Two-layer .kicad_pcb writer (KiCad 8, version 20240108)."""

    def __init__(self, title: str):
        self.title = title
        self.lib_prefix = re.sub(r"[^A-Za-z0-9_-]+", "-", title).strip("-") or "Board"
        self._nets: dict[str, int] = {}
        self._footprints = []   # placed footprint records
        self._segments = []
        self._vias = []
        self._zones = []
        self._graphics = []     # gr_* nodes
        self._outline = None    # (x0, y0, x1, y1)

    # -- nets ---------------------------------------------------------------
    def net(self, name) -> int:
        """Return (allocating if needed) the net number for a net name."""
        name = str(name)
        if name == "":
            return 0
        if name not in self._nets:
            self._nets[name] = len(self._nets) + 1
        return self._nets[name]

    # -- board ----------------------------------------------------------------
    def set_outline(self, w, h, x0=0, y0=0) -> None:
        self._outline = (float(x0), float(y0), float(x0) + float(w), float(y0) + float(h))

    def add_mounting_holes(self, inset=3.5) -> None:
        """4x M2.5 non-plated mounting holes (drill 2.7) at `inset` mm from the
        corners, on net GND.  Refs H1..H4 (mounting holes, exclude from BOM)."""
        if self._outline is None:
            raise ValueError("call set_outline() before add_mounting_holes()")
        x0, y0, x1, y1 = self._outline
        self.net("GND")
        for i, (hx, hy) in enumerate(((x0 + inset, y0 + inset), (x1 - inset, y0 + inset),
                                      (x0 + inset, y1 - inset), (x1 - inset, y1 - inset)), 1):
            fp = Footprint(self.lib_prefix, "MountingHole_M2.5")
            fp.add_pad("", "np_thru_hole", "circle", 0, 0, 3.2, 3.2,
                       layers=("*.Cu", "*.Mask"), drill=2.7, net="GND")
            fp.add_circle(0, 0, 2.6, "F.CrtYd", 0.05)
            self._place(fp, f"H{i}", "MountingHole_M2.5", hx, hy, 0)

    # -- footprints --------------------------------------------------------------
    def add_footprint(self, fp, ref, value, x, y, rot=0) -> None:
        """Place a footprint.  `fp` is either a Footprint (custom inline) or a
        string naming a whitelisted standard-library footprint (SPEC 2.4)."""
        if isinstance(fp, str):
            if fp not in WHITELIST_FOOTPRINTS:
                raise ValueError(
                    f"footprint {fp!r} is not on the SPEC 2.4 whitelist; "
                    "build a custom inline Footprint instead")
            fp = _build_std_footprint(fp)
        elif not isinstance(fp, Footprint):
            raise TypeError("fp must be a Footprint or a whitelisted footprint string")
        if rot % 90:
            raise ValueError("rot must be a multiple of 90")
        self._place(fp, str(ref), str(value), float(x), float(y), int(rot))

    def _place(self, fp: Footprint, ref, value, x, y, rot) -> None:
        if any(f["ref"] == ref for f in self._footprints):
            raise ValueError(f"duplicate footprint ref {ref!r}")
        self._footprints.append({
            "fp": fp, "ref": ref, "value": value, "x": x, "y": y, "rot": rot,
            "uuid": _uuid(),
        })

    def set_pad_net(self, ref, pad_num, net_name) -> None:
        pad_num = str(pad_num)
        for f in self._footprints:
            if f["ref"] == ref:
                for p in f["fp"].pads:
                    if p["num"] == pad_num:
                        p["net"] = None if net_name in (None, "") else str(net_name)
                        if p["net"]:
                            self.net(p["net"])
                        return
                raise ValueError(f"{ref} has no pad {pad_num!r}")
        raise ValueError(f"no footprint with ref {ref!r}")

    # -- copper --------------------------------------------------------------
    def _check_width(self, net_name, width, length=None):
        if str(net_name).upper() in ("GND", "VBUS", "+5V", "+3V3", "12V", "+12V", "VIN",
                                     "LED_5V", "+5V_AC") and width < POWER_RAIL_MIN_WIDTH:
            # Exemption: very short pad-escape / same-net bridge stubs (e.g.
            # bridging two adjacent GND pads on a 0.5 mm pitch WSOF-6) may use
            # the design-rule minimum track width; the rail itself stays >=0.5.
            if length is not None and length <= 2.0 and width >= 0.25:
                return
            raise ValueError(
                f"power rail {net_name} must be routed with width >= "
                f"{POWER_RAIL_MIN_WIDTH} mm (got {width})")

    def segment(self, net_name, x1, y1, x2, y2, layer="F.Cu", width=0.25) -> None:
        if layer not in COPPER_LAYERS:
            raise ValueError(f"segments must be on a copper layer, got {layer!r}")
        self._check_width(net_name, width,
                          length=math.hypot(float(x2) - float(x1),
                                            float(y2) - float(y1)))
        n = self.net(net_name)
        self._segments.append((n, (float(x1), float(y1)), (float(x2), float(y2)),
                               layer, float(width)))

    def route(self, net_name, pts, layer="F.Cu", width=0.25) -> None:
        pts = [(float(x), float(y)) for x, y in pts]
        for a, b in zip(pts, pts[1:]):
            if a != b:
                self.segment(net_name, a[0], a[1], b[0], b[1], layer=layer, width=width)

    def via(self, net_name, x, y) -> None:
        n = self.net(net_name)
        self._vias.append((n, float(x), float(y)))

    def gnd_zone(self, layer="B.Cu") -> None:
        """Full-board GND copper pour (polygon only; KiCad refills)."""
        if self._outline is None:
            raise ValueError("call set_outline() before gnd_zone()")
        self.zone("GND", self._outline, layer=layer)

    def zone(self, net_name, rect, layer="B.Cu") -> None:
        x0, y0, x1, y1 = rect
        n = self.net(net_name)
        self._zones.append({
            "net": n, "net_name": str(net_name), "layer": layer,
            "pts": [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
            "keepout": False, "name": "",
        })

    def keepout_rect(self, x1, y1, x2, y2, note="") -> None:
        """Rule-area keepout over all copper layers (antenna keepout etc.).
        Also drops a note on Dwgs.User when `note` is given."""
        self._zones.append({
            "net": 0, "net_name": "", "layer": None,
            "pts": [(x1, y1), (x2, y1), (x2, y2), (x1, y2)],
            "keepout": True, "name": note or "keepout",
        })
        if note:
            self._graphics.append(
                ["gr_text", _q(note),
                 ["at", _fmt((x1 + x2) / 2), _fmt((y1 + y2) / 2), "0"],
                 ["layer", _q("Dwgs.User")],
                 ["uuid", _q(_uuid())],
                 ["effects", ["font", ["size", "1.5", "1.5"], ["thickness", "0.2"]]]])

    # -- silkscreen -----------------------------------------------------------
    def silk_text(self, txt, x, y, layer="F.Silkscreen", size=1.0) -> None:
        self._graphics.append(
            ["gr_text", _q(txt),
             ["at", _fmt(x), _fmt(y), "0"],
             ["layer", _q(_canon_layer(layer))],
             ["uuid", _q(_uuid())],
             ["effects", ["font", ["size", _fmt(size), _fmt(size)],
                          ["thickness", _fmt(size * 0.15)]]]])

    # -- output ---------------------------------------------------------------
    def _footprint_node(self, f) -> list:
        fp: Footprint = f["fp"]
        node = ["footprint", _q(fp.fp_id),
                ["layer", _q("F.Cu")],
                ["uuid", _q(f["uuid"])],
                ["at", _fmt(f["x"]), _fmt(f["y"])] + ([_fmt(f["rot"])] if f["rot"] else [])]
        ref_effects = ["effects", ["font", ["size", "1", "1"], ["thickness", "0.15"]]]
        node.append(["property", _q("Reference"), _q(f["ref"]),
                     ["at", "0", "-2", "0"], ["layer", _q("F.SilkS")],
                     ["uuid", _q(_uuid())], ref_effects])
        node.append(["property", _q("Value"), _q(f["value"]),
                     ["at", "0", "2", "0"], ["layer", _q("F.Fab")],
                     ["uuid", _q(_uuid())],
                     ["effects", ["font", ["size", "1", "1"], ["thickness", "0.15"]]]])
        node.append(["path", _q("/" + _uuid())])
        node.append(["sheetname", _q("")])
        node.append(["sheetfile", _q(f"{self.title}.kicad_sch")])
        has_th = any(p["kind"] in ("thru_hole", "np_thru_hole") for p in fp.pads)
        node.append(["attr", "through_hole" if has_th else "smd"])
        node.extend(fp.graphics)
        for p in fp.pads:
            pad = ["pad", _q(p["num"]), p["kind"], p["shape"],
                   ["at", _fmt(p["x"]), _fmt(p["y"])],
                   ["size", _fmt(p["sx"]), _fmt(p["sy"])]]
            if p["drill"] is not None:
                pad.append(["drill", _fmt(p["drill"])])
            pad.append(["layers"] + [_q(l) for l in p["layers"]])
            if p["net"]:
                pad.append(["net", str(self.net(p["net"])), _q(p["net"])])
            node.append(pad)
        return node

    def save(self, path) -> None:
        # consistency: every copper item net is declared (they self-declare via
        # net()); ensure the file has net 0 and GND exists when a GND zone was
        # requested implicitly by mounting holes etc.
        if self._outline is None:
            raise ValueError("no board outline; call set_outline() first")

        root = ["kicad_pcb",
                ["version", "20240108"],
                ["generator", _q("pcbnew")],
                ["generator_version", _q("8.0")],
                ["general", ["thickness", "1.6"], ["legacy_teardrops", "no"]],
                ["paper", _q("A4")]]

        layers = ["layers"]
        for entry in KICAD8_LAYERS:
            num, lname, ltype = entry[0], entry[1], entry[2]
            l = [str(num), _q(lname), ltype]
            if len(entry) > 3:
                l.append(_q(entry[3]))
            layers.append(l)
        root.append(layers)

        setup = ["setup",
                 ["pad_to_mask_clearance", "0"],
                 ["allow_soldermask_bridges_in_footprints", "no"],
                 ["grid_origin", _fmt(self._outline[0]), _fmt(self._outline[1])],
                 ["pcbplotparams",
                  ["layerselection", "0x00010fc_ffffffff"],
                  ["plot_on_all_layers_selection", "0x0000000_00000000"],
                  ["disableapertmacros", "false"],
                  ["usegerberextensions", "false"],
                  ["usegerberattributes", "true"],
                  ["usegerberadvancedattributes", "true"],
                  ["creategerberjobfile", "true"],
                  ["dashed_line_dash_ratio", "12.000000"],
                  ["dashed_line_gap_ratio", "3.000000"],
                  ["svguseinch", "false"],
                  ["svgprecision", "4"],
                  ["plotframeref", "false"],
                  ["viasonmask", "false"],
                  ["mode", "1"],
                  ["useauxorigin", "false"],
                  ["hpglpennumber", "1"],
                  ["hpglpenspeed", "20"],
                  ["hpglpendiameter", "15.000000"],
                  ["pdf_front_fp_property_popups", "true"],
                  ["pdf_back_fp_property_popups", "true"],
                  ["dxfpolygonmode", "true"],
                  ["dxfimperialunits", "true"],
                  ["dxfusepcbnewfont", "true"],
                  ["psnegative", "false"],
                  ["psa4output", "false"],
                  ["plotreference", "true"],
                  ["plotvalue", "true"],
                  ["plotfptext", "true"],
                  ["plotinvisibletext", "false"],
                  ["sketchpadsonfab", "false"],
                  ["subtractmaskfromsilk", "false"],
                  ["outputformat", "1"],
                  ["mirror", "false"],
                  ["drillshape", "1"],
                  ["scaleselection", "1"],
                  ["outputdirectory", _q("")]]]
        root.append(setup)

        root.append(["net", "0", _q("")])
        for name, num in sorted(self._nets.items(), key=lambda kv: kv[1]):
            root.append(["net", str(num), _q(name)])

        for f in self._footprints:
            root.append(self._footprint_node(f))

        x0, y0, x1, y1 = self._outline
        root.append(["gr_rect",
                     ["start", _fmt(x0), _fmt(y0)],
                     ["end", _fmt(x1), _fmt(y1)],
                     ["stroke", ["width", "0.1"], ["type", "solid"]],
                     ["fill", "none"],
                     ["layer", _q("Edge.Cuts")],
                     ["uuid", _q(_uuid())]])
        root.extend(self._graphics)

        for n, a, b, layer, width in self._segments:
            root.append(["segment",
                         ["start", _fmt(a[0]), _fmt(a[1])],
                         ["end", _fmt(b[0]), _fmt(b[1])],
                         ["width", _fmt(width)],
                         ["layer", _q(layer)],
                         ["net", str(n)],
                         ["uuid", _q(_uuid())]])
        for n, x, y in self._vias:
            root.append(["via",
                         ["at", _fmt(x), _fmt(y)],
                         ["size", "0.8"], ["drill", "0.4"],
                         ["layers", _q("F.Cu"), _q("B.Cu")],
                         ["net", str(n)],
                         ["uuid", _q(_uuid())]])
        for z in self._zones:
            zone = ["zone", ["net", str(z["net"])], ["net_name", _q(z["net_name"])]]
            if z["keepout"]:
                zone.append(["layers"] + [_q(l) for l in COPPER_LAYERS])
            else:
                zone.append(["layer", _q(z["layer"])])
            zone.append(["uuid", _q(_uuid())])
            if z["keepout"]:
                zone.append(["name", _q(z["name"])])
            zone.append(["hatch", "edge", "0.5"])
            zone.append(["connect_pads", ["clearance", "0.3" if not z["keepout"] else "0"]])
            zone.append(["min_thickness", "0.25"])
            zone.append(["filled_areas_thickness", "no"])
            if z["keepout"]:
                zone.append(["keepout",
                             ["tracks", "not_allowed"], ["vias", "not_allowed"],
                             ["pads", "not_allowed"], ["copperpour", "not_allowed"],
                             ["footprints", "allowed"]])
            zone.append(["fill", "yes",
                         ["thermal_gap", "0.4"], ["thermal_bridge_width", "0.5"]])
            poly = ["polygon", ["pts"] + [["xy", _fmt(px), _fmt(py)] for px, py in z["pts"]]]
            zone.append(poly)
            root.append(zone)

        _write_sexp(path, root)


# ---------------------------------------------------------------------------
# Project file (.kicad_pro) — additive convenience (SPEC 2.5)
# ---------------------------------------------------------------------------


def write_project(path, title: str, lib_name: str) -> None:
    """Write a minimal but valid KiCad 8 .kicad_pro (JSON) with the
    pinned library prefixes pointing at the project-local libs."""
    path = Path(path)
    doc = {
        "board": {
            "design_settings": {
                "defaults": {
                    "board_outline_line_width": 0.1,
                    "copper_line_width": 0.2,
                    "copper_text_size_h": 1.5,
                    "copper_text_size_v": 1.5,
                    "copper_text_thickness": 0.3,
                    "silk_line_width": 0.15,
                    "silk_text_size_h": 1.0,
                    "silk_text_size_v": 1.0,
                    "silk_text_thickness": 0.15,
                },
                "rules": {
                    "min_clearance": 0.2,
                    "min_track_width": 0.25,
                    "min_via_diameter": 0.8,
                    "min_via_annular_width": 0.2,
                    "min_hole_clearance": 0.25,
                    "min_hole_to_hole": 0.25,
                    "min_silk_clearance": 0.15,
                },
                "track_widths": [0.25, 0.5, 1.0],
                "via_dimensions": [{"diameter": 0.8, "drill": 0.4}],
            },
            "layer_presets": [],
        },
        "cvpcb": {"equivalence_files": []},
        "erc": {"meta": {"version": 0}, "pin_map": [], "rule_severities": {}},
        "libraries": {
            "pinned_footprint_libs": [title],
            "pinned_symbol_libs": [lib_name],
        },
        "meta": {"filename": path.name, "version": 1},
        "net_settings": {
            "classes": [{
                "bus_width": 12,
                "clearance": 0.2,
                "diff_pair_gap": 0.25,
                "diff_pair_via_gap": 0.25,
                "diff_pair_width": 0.2,
                "line_style": 0,
                "microvia_diameter": 0.3,
                "microvia_drill": 0.1,
                "name": "Default",
                "pcb_color": "rgba(0, 0, 0, 0.000)",
                "schematic_color": "rgba(0, 0, 0, 0.000)",
                "track_width": 0.25,
                "via_diameter": 0.8,
                "via_drill": 0.4,
                "wire_width": 6,
            }],
            "meta": {"version": 3},
            "net_colors": None,
            "netclass_assignments": None,
            "netclass_patterns": [],
        },
        "pcbnew": {"last_paths": {}, "page_layout_descr_file": ""},
        "schematic": {
            "bom_format_presets": [],
            "bom_fmt_presets": [],
            "bom_presets": [],
            "connection_grid_size": 50.0,
            "drawing": {
                "default_line_thickness": 6.0,
                "default_text_size": 50.0,
                "field_names": [],
                "intersheets_ref_own_page": False,
                "intersheets_ref_prefix": "",
                "intersheets_ref_short": False,
                "intersheets_ref_show": False,
                "intersheets_ref_suffix": "",
                "junction_size_choice": 3,
                "label_size_ratio": 0.375,
                "pin_symbol_size": 25.0,
                "text_offset_ratio": 0.15,
            },
            "legacy_lib_dir": "",
            "legacy_lib_list": [],
            "meta": {"version": 1},
            "page_layout_descr_file": "",
            "plot_directory": "",
            "spice_adjust_passive_values": False,
            "spice_external_command": "spice \"%I\"",
            "subpart_first_id": 65,
            "subpart_id_separator": 0,
        },
        "sheets": [[_uuid(), ""]],
        "text_variables": {},
    }
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# validate_project
# ---------------------------------------------------------------------------


def _sch_extract(root):
    """Pull connectivity + components out of a parsed schematic."""
    lib_symbols = {}
    ls = find_first(root, "lib_symbols")
    if ls:
        for sym in find_all(ls, "symbol"):
            name = str(sym[1]) if len(sym) > 1 else ""
            bare = name.split(":")[-1]
            tail = bare.rsplit("_", 2)
            if len(tail) == 3 and tail[-1].isdigit() and tail[-2].isdigit():
                continue  # sub-unit
            pins = {}
            for sub in find_all(sym, "symbol"):
                for pin in find_all(sub, "pin"):
                    at = get_at(pin)
                    num_node = find_first(pin, "number")
                    if at and num_node:
                        pins[str(num_node[1])] = (at[0], at[1])
            lib_symbols[name] = {
                "pins": pins,
                "is_power": find_first(sym, "power") is not None,
            }

    comps = []
    for sym in find_all(root, "symbol"):
        lib_id = None
        for c in sym:
            if isinstance(c, list) and c and c[0] == "lib_id":
                lib_id = str(c[1])
        if lib_id is None:
            continue
        at = get_at(sym) or (0.0, 0.0, 0.0)
        comps.append({
            "lib_id": lib_id,
            "ref": get_prop(sym, "Reference") or "?",
            "value": get_prop(sym, "Value") or "",
            "on_board": "no" not in [str(x) for c in find_all(sym, "on_board") for x in c[1:]],
            "x": at[0], "y": at[1], "rot": at[2],
            "uuid_node": find_first(sym, "uuid"),
        })

    wires, labels, glabels, ncs, junctions = [], [], [], [], []
    for w in find_all(root, "wire"):
        pts = [tuple(map(float, xy[1:3])) for xy in find_all(find_first(w, "pts") or [], "xy")]
        if len(pts) >= 2:
            wires.append((pts[0], pts[1]))
    for lb in find_all(root, "label"):
        at = get_at(lb)
        if at and len(lb) > 1:
            labels.append((str(lb[1]), (at[0], at[1])))
    for lb in find_all(root, "global_label"):
        at = get_at(lb)
        name = None
        for tok in lb[1:]:
            if isinstance(tok, str):
                name = tok
                break
        if at and name:
            glabels.append((name, (at[0], at[1])))
    for nc in find_all(root, "no_connect"):
        at = get_at(nc)
        if at:
            ncs.append((at[0], at[1]))
    for j in find_all(root, "junction"):
        at = get_at(j)
        if at:
            junctions.append((at[0], at[1]))
    return lib_symbols, comps, wires, labels, glabels, ncs, junctions


def validate_project(board_dir) -> list[str]:
    """Validate one board directory.  Returns a list of problems ([] = pass)."""
    problems: list[str] = []
    d = Path(board_dir)
    if not d.is_dir():
        return [f"not a directory: {board_dir}"]

    pro = sorted(d.glob("*.kicad_pro"))
    sch = sorted(d.glob("*.kicad_sch"))
    pcb = sorted(d.glob("*.kicad_pcb"))
    sym = sorted(d.glob("*.kicad_sym"))
    for kind, files in ((".kicad_pro", pro), (".kicad_sch", sch),
                        (".kicad_pcb", pcb), (".kicad_sym", sym)):
        if not files:
            problems.append(f"missing *{kind} in {d}")

    # --- .kicad_pro: valid JSON ----------------------------------------------
    for f in pro:
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
            if "libraries" not in doc or "meta" not in doc:
                problems.append(f"{f.name}: missing 'libraries' or 'meta' key")
        except Exception as e:
            problems.append(f"{f.name}: invalid JSON: {e}")

    # --- parse S-expressions ---------------------------------------------------
    sch_root = pcb_root = None
    sym_roots = []
    for f in sch:
        try:
            sch_root = sexp_parse_file(f)
            if not sch_root or sch_root[0] != "kicad_sch":
                problems.append(f"{f.name}: root is not kicad_sch")
        except Exception as e:
            problems.append(f"{f.name}: parse error: {e}")
    for f in pcb:
        try:
            pcb_root = sexp_parse_file(f)
            if not pcb_root or pcb_root[0] != "kicad_pcb":
                problems.append(f"{f.name}: root is not kicad_pcb")
        except Exception as e:
            problems.append(f"{f.name}: parse error: {e}")
    for f in sym:
        try:
            r = sexp_parse_file(f)
            if not r or r[0] != "kicad_symbol_lib":
                problems.append(f"{f.name}: root is not kicad_symbol_lib")
            sym_roots.append((f, r))
        except Exception as e:
            problems.append(f"{f.name}: parse error: {e}")

    # --- unique uuids across schematic + pcb -----------------------------------
    uuid_re = re.compile(r"\(uuid\s+([0-9A-Fa-f-]{36})\)")
    seen_uuids: dict[str, str] = {}
    for f in list(sch) + list(pcb):
        if f.exists():
            for m in uuid_re.finditer(f.read_text(encoding="utf-8", errors="replace")):
                u = m.group(1)
                if u in seen_uuids:
                    problems.append(f"duplicate uuid {u} in {f.name} and {seen_uuids[u]}")
                else:
                    seen_uuids[u] = f.name

    # --- schematic checks --------------------------------------------------------
    sch_nets: set[str] = set()
    sch_board_refs: set[str] = set()
    if sch_root and sch_root[0] == "kicad_sch":
        lib_symbols, comps, wires, labels, glabels, ncs, junctions = _sch_extract(sch_root)

        # unique refs
        refs: dict[str, int] = {}
        for c in comps:
            refs[c["ref"]] = refs.get(c["ref"], 0) + 1
        for ref, n in refs.items():
            if n > 1:
                problems.append(f"duplicate reference {ref} ({n} instances)")
            if not ref.startswith("#"):
                sch_board_refs.add(ref)

        # connectivity: union-find over wire endpoints and attachment points
        parent: dict = {}

        def find(k):
            parent.setdefault(k, k)
            while parent[k] != k:
                parent[k] = parent[parent[k]]
                k = parent[k]
            return k

        def union(a, b):
            parent[find(a)] = find(b)

        pin_points = []  # (ref, num, pt, is_power, power_value)
        for c in comps:
            sd = lib_symbols.get(c["lib_id"])
            if sd is None:
                problems.append(f"{c['ref']}: lib_id {c['lib_id']!r} not in lib_symbols")
                continue
            for num, (px, py) in sd["pins"].items():
                pt = _sch_pin_abs(c["x"], c["y"], c["rot"], px, py)
                pin_points.append((c["ref"], num, pt, sd["is_power"], c["value"]))

        attach = [pt for _, _, pt, _, _ in pin_points]
        attach += [p for _, p in labels] + [p for _, p in glabels] + ncs + junctions
        for a, b in wires:
            union(("pt", a), ("pt", b))
            for p in attach:
                if Schematic._on_segment(p, a, b):
                    union(("pt", a), ("pt", p))

        wired_roots = {find(("pt", a)) for a, _ in wires}
        label_pts = {p for _, p in labels} | {p for _, p in glabels}
        nc_set = set(ncs)
        for ref, num, pt, _is_power, _val in pin_points:
            if pt in nc_set or pt in label_pts:
                continue
            if ("pt", pt) in parent and find(("pt", pt)) in wired_roots:
                continue
            problems.append(f"unresolved pin {ref} pad {num} at ({pt[0]}, {pt[1]})")

        # schematic net names: labels + global labels + power symbol values
        sch_nets = {n for n, _ in labels} | {n for n, _ in glabels}
        sch_nets |= {c["value"] for c in comps
                     if (lib_symbols.get(c["lib_id"]) or {}).get("is_power")}

    # --- pcb checks ---------------------------------------------------------------
    if pcb_root and pcb_root[0] == "kicad_pcb":
        net_decls: dict[int, str] = {}
        for n in find_all(pcb_root, "net"):
            if len(n) >= 3:
                net_decls[int(n[1])] = str(n[2])
        if net_decls.get(0, "") != "":
            problems.append("net 0 must be the unnamed net (net 0 \"\")")

        pcb_refs = set()
        pcb_mech_refs = set()  # H<n> mounting holes: PCB-only by design (SPEC 2.2)
        pad_problems = []
        for fp in find_all(pcb_root, "footprint"):
            ref = get_prop(fp, "Reference") or "?"
            if re.fullmatch(r"H\d+", ref):
                pcb_mech_refs.add(ref)
            else:
                pcb_refs.add(ref)
            for pad in find_all(fp, "pad"):
                for net_node in find_all(pad, "net"):
                    if len(net_node) >= 2:
                        num = int(net_node[1])
                        pname = str(net_node[2]) if len(net_node) > 2 else None
                        if num not in net_decls:
                            pad_problems.append(f"{ref} pad {pad[1]}: net {num} not declared")
                        elif pname is not None and pname != net_decls[num]:
                            pad_problems.append(
                                f"{ref} pad {pad[1]}: net {num} name mismatch "
                                f"({pname!r} != {net_decls[num]!r})")
        problems.extend(pad_problems)

        # PCB net names subset of schematic net names (+ unnamed)
        if sch_root and sch_root[0] == "kicad_sch":
            for num, name in net_decls.items():
                if num == 0:
                    continue
                if name not in sch_nets:
                    problems.append(
                        f"pcb net {num} {name!r} has no matching schematic net name")

        # footprint refs match schematic refs (schematic on_board, non-# refs)
        if sch_root and sch_root[0] == "kicad_sch":
            for ref in sorted(pcb_refs - sch_board_refs):
                problems.append(f"pcb footprint {ref} has no schematic symbol")
            for ref in sorted(sch_board_refs - pcb_refs):
                problems.append(f"schematic symbol {ref} has no pcb footprint")

    return problems


if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) != 2:
        print("usage: python3 kicadgen.py <board_dir>")
        sys.exit(2)
    issues = validate_project(sys.argv[1])
    if issues:
        print(f"FAIL: {len(issues)} problem(s) in {sys.argv[1]}")
        for p in issues:
            print("  -", p)
        sys.exit(1)
    print(f"OK: {sys.argv[1]} passes validate_project")
