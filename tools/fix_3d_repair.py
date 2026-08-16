#!/usr/bin/env python3
"""Repair PCBs corrupted by fix_3d.py (stale-offset insertions) and re-patch idempotently."""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def root_end(s):
    d = 0
    for i, c in enumerate(s):
        if c == '(':
            d += 1
        elif c == ')':
            d -= 1
            if d == 0:
                return i
    return len(s) - 1

def fp_end(txt, start):
    d, i = 0, start
    while i < len(txt):
        c = txt[i]
        if c == '(':
            d += 1
        elif c == ')':
            d -= 1
            if d == 0:
                return i
        i += 1
    return len(txt) - 1

# model index from disk
model_index = {}
for wrl in glob.glob(os.path.join(ROOT, "3dmodels", "*", "*.wrl")):
    rel = os.path.relpath(wrl, ROOT)
    model_index[os.path.splitext(os.path.basename(wrl))[0]] = rel

ALIASES = {
    "ESP32-C6-WROOM-1": ["ESP32-C6-WROOM-1", "ESP32-WROOM-32"],
    "BMP280-LGA8": ["BMP280", "BME280"],
}
def candidates(fp):
    base = fp.split(":")[-1]
    out = [base]
    out += ALIASES.get(base, [])
    for k in model_index:
        kb = k.split("_")[0]
        if base.split("-")[0] == kb and len(kb) > 4:
            out.append(k)
    return out

for pcb in glob.glob(os.path.join(ROOT, "boards", "*", "*.kicad_pcb")):
    txt = open(pcb).read()
    board = os.path.basename(os.path.dirname(pcb))
    e = root_end(txt)
    if txt[e + 1:].strip():
        txt = txt[:e + 1] + "\n"  # strip garbage
    # collect footprint matches first, patch in REVERSE order
    matches = list(re.finditer(r'\(footprint\s+"([^"]+)"', txt))
    n = 0
    for m in reversed(matches):
        fp = m.group(1)
        fe = fp_end(txt, m.start())
        block = txt[m.start():fe]
        if "(model " in block:
            continue
        model = None
        for cand in candidates(fp):
            if cand in model_index:
                model = model_index[cand]
                break
        if not model:
            continue
        ins = (f'\n    (model "${{KIPRJMOD}}/../../{model}"\n'
               f'      (hide yes)\n      (offset (xyz 0 0 0))\n'
               f'      (scale (xyz 1 1 1))\n      (rotate (xyz 0 0 0)))')
        txt = txt[:fe] + ins + txt[fe:]
        n += 1
    open(pcb, "w").write(txt)
    print(board, "patched", n)

# revalidate
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kicadgen
for d in sorted(glob.glob(os.path.join(ROOT, "boards", "*"))):
    if not os.path.isdir(d):
        continue
    name = os.path.basename(d)
    if name in ("analysis", "wave2"):
        continue
    try:
        r = kicadgen.validate_project(d)
        print(name, "VALID" if not r else f"PROBLEMS: {r}")
    except Exception as ex:
        print(name, "EXC", ex)

man = {k: {"wrl": v} for k, v in sorted(model_index.items())}
json.dump(man, open(os.path.join(ROOT, "3dmodels", "manifest.json"), "w"), indent=1)
print("manifest models:", len(man))
