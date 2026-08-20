#!/usr/bin/env python3
"""fix_3d.py — fill missing 3D models, rebuild manifest from actual PCBs,
patch (model ...) refs into every board .kicad_pcb, revalidate."""
import glob, json, os, re, subprocess, sys, time

ROOT = "/mnt/agents/output/home-automation-pcbs"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
MIRROR = "https://raw.githubusercontent.com/KiCad/kicad-packages3D/master/{lib}.3dshapes/{model}.{ext}"

def curl(url, path, minb=200):
    r = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", "60", "-o", path, url],
                       capture_output=True)
    return r.returncode == 0 and os.path.exists(path) and os.path.getsize(path) > minb

def kicad_mirror(lib, model, outdir):
    os.makedirs(outdir, exist_ok=True)
    got = {}
    for ext in ("wrl", "step"):
        p = os.path.join(outdir, f"{model}.{ext}")
        if os.path.exists(p) or curl(MIRROR.format(lib=lib, model=model, ext=ext), p):
            got[ext] = os.path.relpath(p, os.path.join(ROOT, "3dmodels"))
    return got or None

def easyeda(lcsc, outdir):
    os.makedirs(outdir, exist_ok=True)
    tmp = f"/tmp/e2k_{lcsc}"
    try:
        subprocess.run(["easyeda2kicad", "--lcsc_id", lcsc, "--full", "--output", tmp],
                       capture_output=True, timeout=150)
    except Exception:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "easyeda2kicad"],
                           capture_output=True)
            subprocess.run(["easyeda2kicad", "--lcsc_id", lcsc, "--full", "--output", tmp],
                           capture_output=True, timeout=150)
        except Exception:
            return None
    got = {}
    shapes = tmp + ".3dshapes"
    if os.path.isdir(shapes):
        import shutil
        for f in os.listdir(shapes):
            ext = f.rsplit(".", 1)[-1].lower()
            if ext in ("wrl", "step"):
                dst = os.path.join(outdir, f)
                shutil.copy(os.path.join(shapes, f), dst)
                got[ext] = os.path.relpath(dst, os.path.join(ROOT, "3dmodels"))
    return got or None

# 1. targeted fetches for known-missing real parts
TARGETS = [  # (lcsc, footprint-lib, footprint-name)
    ("C5366877", "Shared", "ESP32-C6-WROOM-1"),
    ("C92466", "Shared", "BMP280-LGA8"),
    ("C139797", "Shared", "Tactile-6x6-SMD"),
    ("C8678", "Diode_SMD", "D_SMA"),
    ("C55528", "Shared", "IR-LED-5mm"),
    ("C49258", "Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Vertical"),
    ("C492407", "Connector_PinHeader_2.54mm", "PinHeader_1x08_P2.54mm_Vertical"),
    ("C8465", "Shared", "TerminalBlock-5.08-2P"),
    ("C2691448", "Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Vertical"),
    ("C165948", "Connector_USB", "USB_C_Receptacle_USB2.0_16P"),
]
STD_LIBS = ("Resistor_SMD", "Capacitor_SMD", "LED_SMD", "Diode_SMD",
            "Package_TO_SOT_SMD", "Package_SO", "Connector_USB",
            "Connector_PinHeader_2.54mm", "Fuse")

results = {}
for lcsc, lib, name in TARGETS:
    outdir = os.path.join(ROOT, "3dmodels", f"{lib}.3dshapes" if lib in STD_LIBS else "Shared.3dshapes")
    got = kicad_mirror(lib, name, outdir) if lib in STD_LIBS else None
    if not got:
        got = easyeda(lcsc, os.path.join(ROOT, "3dmodels", "Shared.3dshapes"))
    results[name] = got
    print(name, "->", "OK" if got else "missing", got)
    time.sleep(0.4)

# 2. scan actual PCBs, build name->model index from everything on disk
model_index = {}  # footprint name -> rel wrl path
for d in glob.glob(os.path.join(ROOT, "3dmodels", "*.3dshapes")):
    for f in os.listdir(d):
        if f.endswith(".wrl"):
            model_index[f[:-4]] = os.path.relpath(os.path.join(d, f), ROOT)

# name aliases across board-local libs
def candidates(fpname):
    base = fpname.split(":")[-1]
    yield base
    for alias, target in [("ESP32-C6-WROOM-1", "ESP32-C6-WROOM-1"),
                          ("ESP32-C3-WROOM-02", "ESP32-C3-WROOM-02"),
                          ("SHT31-DFN8", "DFN-8_L2.5-W2.5-H1.0-P0.50")]:
        if base.startswith(alias):
            yield target
    # easyeda model names contain package names; fuzzy: match by containment
    for k in model_index:
        kb = k.split("_")[0]
        if base.split("-")[0] == kb and len(kb) > 4:
            yield k

# 3. patch each pcb
patched = {}
for pcb in glob.glob(os.path.join(ROOT, "boards", "*", "*.kicad_pcb")):
    txt = open(pcb).read()
    board = os.path.basename(os.path.dirname(pcb))
    n = 0
    for m in re.finditer(r'\(footprint\s+"([^"]+)"', txt):
        fp = m.group(1)
        if re.search(r'\(model\s', txt[m.start():m.start()+4000]):
            continue
        model = None
        for cand in candidates(fp):
            if cand in model_index:
                model = model_index[cand]; break
        if not model:
            continue
        ins = (f'\n    (model "${{KIPRJMOD}}/../../{model}"\n'
               f'      (hide yes)\n      (offset (xyz 0 0 0))\n'
               f'      (scale (xyz 1 1 1))\n      (rotate (xyz 0 0 0)))')
        # insert before the footprint's closing paren: find matching close
        depth, i = 0, m.start()
        while i < len(txt):
            c = txt[i]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        txt = txt[:i] + ins + txt[i:]
        n += 1
    open(pcb, "w").write(txt)
    patched[board] = n
print("patched:", patched)

# 4. final manifest
man = {k: {"wrl": v} for k, v in sorted(model_index.items())}
json.dump(man, open(os.path.join(ROOT, "3dmodels", "manifest.json"), "w"), indent=1)

# 5. revalidate all boards
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kicadgen
for d in sorted(glob.glob(os.path.join(ROOT, "boards", "*"))):
    if not glob.glob(os.path.join(d, "*.kicad_pcb")):
        continue
    b = os.path.basename(d)
    r = kicadgen.validate_project(d)
    print(b, "VALID" if not r else f"PROBLEMS: {r[:3]}")
