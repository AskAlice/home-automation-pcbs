#!/usr/bin/env python3
"""render_pcb.py — rasterize a .kicad_pcb (KiCad 8) to a PNG without KiCad.

Parses the S-expression file (using the vendored kicad-happy sexp parser,
falling back to a minimal built-in one) and draws: substrate, zones, tracks,
vias, pads, silkscreen, edge cuts. Top view (F.Cu) and bottom view (B.Cu).

Usage: python3 render_pcb.py <board.kicad_pcb> <out_prefix> [--scale 20]
Writes <out_prefix>_top.png and <out_prefix>_bottom.png
"""
import math
import os
import sys

sys.path.insert(0, "/mnt/agents/output/.kicad-happy/skills/kicad/scripts")
try:
    from sexp_parser import parse_file
except Exception:
    parse_file = None

from PIL import Image, ImageDraw, ImageFont

# ---------- tiny fallback s-expr parser ----------
def _mini_parse(text):
    import re
    toks = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', text)
    pos = 0
    def rec():
        nonlocal pos
        out = []
        while pos < len(toks):
            t = toks[pos]; pos += 1
            if t == '(':
                out.append(rec())
            elif t == ')':
                return out
            else:
                out.append(t.strip('"'))
        return out
    return rec()

def parse(path):
    if parse_file:
        return parse_file(path)
    return _mini_parse(open(path).read())

def find_all(node, kw, out=None):
    if out is None: out = []
    if isinstance(node, list):
        if node and node[0] == kw:
            out.append(node)
        for c in node:
            find_all(c, kw, out)
    return out

def num(x, d=0.0):
    try: return float(x)
    except Exception: return d

def at_of(node):
    """Return (x, y, rot) from an (at x y [rot]) child."""
    for c in node:
        if isinstance(c, list) and c and c[0] == 'at':
            x, y = num(c[1]), num(c[2])
            r = num(c[3]) if len(c) > 3 else 0.0
            return x, y, r
    return 0.0, 0.0, 0.0

def rot_pt(dx, dy, deg):
    a = math.radians(deg)
    return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)

# ---------- colors (KiCad-ish) ----------
SUBSTRATE = (12, 40, 28)        # dark pcb green
SUBSTRATE_B = (10, 34, 24)
F_CU = (196, 52, 46)
B_CU = (68, 84, 190)
PAD_F = (210, 170, 60)
PAD_B = (170, 140, 60)
HOLE = (8, 8, 8)
SILK = (235, 235, 230)
EDGE = (245, 230, 120)
KEEPOUT = (120, 60, 140, 60)
ZONE_F = (196, 52, 46, 40)
ZONE_B = (68, 84, 190, 45)

def collect(pcb):
    """Extract drawable primitives."""
    prims = dict(edge=[], segF=[], segB=[], via=[], padF=[], padB=[], hole=[],
                 silk=[], text=[], zones=[], keepouts=[])
    for fp in find_all(pcb, 'footprint'):
        fx, fy, fr = at_of(fp)
        layer = 'F.Cu'
        for c in fp:
            if isinstance(c, list) and c and c[0] == 'layer':
                layer = c[1]
        flip = layer.startswith('B.')
        for pad in find_all(fp, 'pad'):
            ptype = pad[2] if len(pad) > 2 else ''
            px, py, pr = at_of(pad)
            size = None
            for c in pad:
                if isinstance(c, list) and c and c[0] == 'size':
                    size = (num(c[1]), num(c[2]))
            drill = None
            for c in pad:
                if isinstance(c, list) and c and c[0] == 'drill':
                    drill = num(c[1])
            shape = pad[3] if len(pad) > 3 else 'rect'
            # transform to board coords
            dx, dy = (px, -py) if flip else (px, py)
            rx, ry = rot_pt(dx, dy, -fr if flip else fr)
            # KiCad pad local y-axis flip on B side: good enough for render
            ax, ay = fx + rx, fy + ry
            layers = []
            for c in pad:
                if isinstance(c, list) and c and c[0] == 'layers':
                    layers = c[1:]
            if ptype in ('thru_hole', 'np_thru_hole') and drill:
                prims['hole'].append((ax, ay, drill, size[0] if size else drill + 0.5, ptype))
            if size:
                onF = any('F.Cu' in str(l) or '*.Cu' in str(l) for l in layers)
                onB = any('B.Cu' in str(l) or '*.Cu' in str(l) for l in layers)
                if ptype == 'thru_hole': onF = onB = True
                ang = -fr if flip else fr
                rr = math.radians(ang + pr)
                if onF: prims['padF'].append((ax, ay, size[0], size[1], rr, shape))
                if onB: prims['padB'].append((ax, ay, size[0], size[1], rr, shape))
        # silkscreen lines + texts
        for ln in find_all(fp, 'fp_line'):
            lay = None
            for c in ln:
                if isinstance(c, list) and c and c[0] == 'layer': lay = c[1]
            if lay not in ('F.Silkscreen', 'B.Silkscreen'): continue
            st = en = None
            for c in ln:
                if isinstance(c, list) and c and c[0] == 'start': st = (num(c[1]), num(c[2]))
                if isinstance(c, list) and c and c[0] == 'end': en = (num(c[1]), num(c[2]))
            if st and en:
                s = rot_pt(*st, fr); e = rot_pt(*en, fr)
                prims['silk'].append((fx + s[0], fy + s[1], fx + e[0], fy + e[1], lay))
        for tx in find_all(fp, 'fp_text'):
            if len(tx) > 2 and tx[1] in ('reference', 'value'):
                x, y, r = at_of(tx)
                off = rot_pt(x, y, fr)
                prims['text'].append((fx + off[0], fy + off[1], str(tx[2])))
        for prop in find_all(fp, 'property'):
            if len(prop) > 2 and prop[1] == 'Reference':
                x, y, r = at_of(prop)
                off = rot_pt(x, y, fr)
                prims['text'].append((fx + off[0], fy + off[1], str(prop[2]).strip('"')))
    for seg in find_all(pcb, 'segment'):
        st = en = None; w = 0.25; lay = 'F.Cu'
        for c in seg:
            if isinstance(c, list) and c and c[0] == 'start': st = (num(c[1]), num(c[2]))
            if isinstance(c, list) and c and c[0] == 'end': en = (num(c[1]), num(c[2]))
            if isinstance(c, list) and c and c[0] == 'width': w = num(c[1])
            if isinstance(c, list) and c and c[0] == 'layer': lay = c[1]
        if st and en:
            prims['segF' if lay == 'F.Cu' else 'segB'].append((st[0], st[1], en[0], en[1], w))
    for v in find_all(pcb, 'via'):
        x, y, _ = at_of(v); d = 0.4; s = 0.8
        for c in v:
            if isinstance(c, list) and c and c[0] == 'size': s = num(c[1])
            if isinstance(c, list) and c and c[0] == 'drill': d = num(c[1])
        prims['via'].append((x, y, s, d))
    for z in find_all(pcb, 'zone'):
        lay = 'B.Cu'
        for c in z:
            if isinstance(c, list) and c and c[0] == 'layer': lay = c[1]
        for poly in find_all(z, 'polygon'):
            for pts in find_all(poly, 'pts'):
                xy = [(num(p[1]), num(p[2])) for p in pts if isinstance(p, list) and p and p[0] == 'xy']
                if xy: prims['zones'].append((xy, lay))
    for k in find_all(pcb, 'zone'):
        pass
    for gr in find_all(pcb, 'gr_rect') + find_all(pcb, 'gr_line') + find_all(pcb, 'gr_poly'):
        lay = ''
        for c in gr:
            if isinstance(c, list) and c and c[0] == 'layer': lay = c[1]
        if 'Edge.Cuts' not in str(lay): continue
        if gr[0] == 'gr_rect':
            st = en = None
            for c in gr:
                if isinstance(c, list) and c and c[0] == 'start': st = (num(c[1]), num(c[2]))
                if isinstance(c, list) and c and c[0] == 'end': en = (num(c[1]), num(c[2]))
            if st and en: prims['edge'].append(('rect', st, en))
        elif gr[0] == 'gr_line':
            st = en = None
            for c in gr:
                if isinstance(c, list) and c and c[0] == 'start': st = (num(c[1]), num(c[2]))
                if isinstance(c, list) and c and c[0] == 'end': en = (num(c[1]), num(c[2]))
            if st and en: prims['edge'].append(('line', st, en))
    for ko in find_all(pcb, 'zone'):  # keepouts have (keepout ...) inside
        koflags = find_all(ko, 'keepout')
        if koflags:
            for poly in find_all(ko, 'polygon'):
                for pts in find_all(poly, 'pts'):
                    xy = [(num(p[1]), num(p[2])) for p in pts if isinstance(p, list) and p and p[0] == 'xy']
                    if xy: prims['keepouts'].append(xy)
    return prims

def render(prims, side, out_path, scale):
    xs, ys = [], []
    for kind, st, en in prims['edge']:
        xs += [st[0], en[0]]; ys += [st[1], en[1]]
    if not xs:
        for lst, key in ((prims['segF'], None), (prims['segB'], None)):
            for s in lst: xs += [s[0], s[2]]; ys += [s[1], s[3]]
    x0, x1, y0, y1 = min(xs) - 4, max(xs) + 4, min(ys) - 4, max(ys) + 4
    W, H = int((x1 - x0) * scale), int((y1 - y0) * scale)
    img = Image.new('RGB', (W, H), (24, 24, 28))
    dr = ImageDraw.Draw(img, 'RGBA')
    def T(x, y):
        return ((x - x0) * scale, (y - y0) * scale)
    # substrate = edge outline bbox (rect boards)
    dr.rectangle([T(x0 + 4, y0 + 4), T(x1 - 4, y1 - 4)], fill=SUBSTRATE if side == 'F' else SUBSTRATE_B)
    # zones
    for xy, lay in prims['zones']:
        if (side == 'F') != (lay == 'F.Cu'): continue
        dr.polygon([T(x, y) for x, y in xy], fill=ZONE_F if side == 'F' else ZONE_B)
    # tracks
    segs = prims['segF'] if side == 'F' else prims['segB']
    col = F_CU if side == 'F' else B_CU
    for x1_, y1_, x2_, y2_, w in segs:
        dr.line([T(x1_, y1_), T(x2_, y2_)], fill=col, width=max(1, int(w * scale)))
    # pads
    pads = prims['padF'] if side == 'F' else prims['padB']
    pcol = PAD_F if side == 'F' else PAD_B
    for x, y, sx, sy, ang, shape in pads:
        cx, cy = T(x, y)
        if shape in ('oval', 'circle') or abs(sx - sy) < 1e-6:
            rx, ry = sx * scale / 2, sy * scale / 2
            dr.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=pcol)
        else:
            rx, ry = sx * scale / 2, sy * scale / 2
            ca, sa = math.cos(ang), math.sin(ang)
            pts = []
            for dx, dy in ((-rx, -ry), (rx, -ry), (rx, ry), (-rx, ry)):
                pts.append((cx + dx * ca - dy * sa, cy + dx * sa + dy * ca))
            dr.polygon(pts, fill=pcol)
    # vias + holes
    for x, y, s, d in prims['via']:
        cx, cy = T(x, y)
        dr.ellipse([cx - s * scale / 2, cy - s * scale / 2, cx + s * scale / 2, cy + s * scale / 2], fill=(200, 190, 150))
        dr.ellipse([cx - d * scale / 2, cy - d * scale / 2, cx + d * scale / 2, cy + d * scale / 2], fill=HOLE)
    for x, y, d, s, t in prims['hole']:
        cx, cy = T(x, y)
        if t == 'thru_hole':
            dr.ellipse([cx - s * scale / 2, cy - s * scale / 2, cx + s * scale / 2, cy + s * scale / 2], fill=pcol)
        dr.ellipse([cx - d * scale / 2, cy - d * scale / 2, cx + d * scale / 2, cy + d * scale / 2], fill=HOLE)
    # keepouts
    for xy in prims['keepouts']:
        dr.polygon([T(x, y) for x, y in xy], outline=(150, 80, 200), width=2)
    # silkscreen
    for x1_, y1_, x2_, y2_, lay in prims['silk']:
        if (side == 'F') != (lay == 'F.Silkscreen'): continue
        dr.line([T(x1_, y1_), T(x2_, y2_)], fill=SILK, width=2)
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', max(8, int(0.9 * scale)))
    except Exception:
        font = ImageFont.load_default()
    for x, y, t in prims['text']:
        if side == 'B': continue
        cx, cy = T(x, y)
        dr.text((cx, cy), t, fill=SILK, font=font, anchor='mm')
    # edge
    for kind, st, en in prims['edge']:
        if kind == 'rect':
            dr.rectangle([T(*st), T(*en)], outline=EDGE, width=3)
        else:
            dr.line([T(*st), T(*en)], fill=EDGE, width=3)
    img.save(out_path)

if __name__ == '__main__':
    pcb_path, out_prefix = sys.argv[1], sys.argv[2]
    scale = 20
    if '--scale' in sys.argv:
        scale = float(sys.argv[sys.argv.index('--scale') + 1])
    doc = parse(pcb_path)
    prims = collect(doc)
    render(prims, 'F', out_prefix + '_top.png', scale)
    render(prims, 'B', out_prefix + '_bottom.png', scale)
    print('rendered', out_prefix + '_top.png', out_prefix + '_bottom.png')
