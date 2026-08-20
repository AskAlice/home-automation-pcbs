#!/usr/bin/env python3
"""fetch_3d.py — fetch 3D models (STEP+WRL) for all BOM parts.

Standard KiCad packages -> KiCad packages3D GitHub mirror.
Everything else with an LCSC number -> easyeda2kicad (EasyEDA/LCSC 3D).
Output: 3dmodels/Shared.3dshapes/<Model>.{wrl,step} + 3dmodels/manifest.json
mapping "lib:footprint" -> model info.
"""
import csv, glob, json, os, re, shutil, subprocess, sys, time, urllib.request

ROOT = "/mnt/agents/output/home-automation-pcbs"
OUTDIR = os.path.join(ROOT, "3dmodels", "Shared.3dshapes")
os.makedirs(OUTDIR, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
MIRROR = "https://raw.githubusercontent.com/KiCad/kicad-packages3D/master/{lib}.3dshapes/{model}.{ext}"

def dl(url, path, magic=None):
    try:
        req = urllib.request.Request(url, headers=UA)
        data = urllib.request.urlopen(req, timeout=30).read()
        if magic and not data.startswith(magic):
            return False
        if len(data) < 200:
            return False
        open(path, "wb").write(data)
        return True
    except Exception:
        return False

def kicad_mirror(lib, model):
    got = {}
    for ext in ("wrl", "step"):
        p = os.path.join(OUTDIR, f"{model}.{ext}")
        if os.path.exists(p) or dl(MIRROR.format(lib=lib, model=model, ext=ext), p):
            got[ext] = f"Shared.3dshapes/{model}.{ext}"
    return got or None

def easyeda(lcsc, model_hint):
    try:
        subprocess.run([sys.executable, "-c", "import easyeda2kicad"],
                       check=True, capture_output=True)
    except Exception:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                        "easyeda2kicad"], capture_output=True)
    tmp = f"/tmp/e2k_{lcsc}"
    try:
        r = subprocess.run(["easyeda2kicad", "--lcsc_id", lcsc, "--full",
                            "--output", tmp], capture_output=True, timeout=120)
    except Exception:
        return None
    shapes = tmp + ".3dshapes"
    got = {}
    if os.path.isdir(shapes):
        for f in os.listdir(shapes):
            ext = f.rsplit(".", 1)[-1].lower()
            if ext not in ("wrl", "step"):
                continue
            base = re.sub(r"[^\w.-]", "_", f.rsplit(".", 1)[0])[:80]
            dst = os.path.join(OUTDIR, f"{base}.{ext}")
            shutil.copy(os.path.join(shapes, f), dst)
            got[ext] = f"Shared.3dshapes/{base}.{ext}"
    return got or None

def main():
    rows = []
    for f in glob.glob(os.path.join(ROOT, "boards", "*", "bom_lcsc.csv")):
        with open(f) as fh:
            rr = list(csv.reader(fh))
        hdr = [h.strip().lower() for h in rr[0]]
        try:
            i_fp = hdr.index("footprint"); i_lcsc = hdr.index("lcsc"); i_mpn = hdr.index("mpn")
        except ValueError:
            i_fp, i_lcsc, i_mpn = 2, 3, 4
        for r in rr[1:]:
            if len(r) > max(i_fp, i_lcsc, i_mpn):
                rows.append((r[i_fp].strip(), r[i_lcsc].strip(), r[i_mpn].strip()))
    uniq = {}
    for fp, lcsc, mpn in rows:
        uniq[fp] = (lcsc, mpn)
    manifest = {}
    for fp, (lcsc, mpn) in sorted(uniq.items()):
        lib, _, name = fp.partition(":")
        name = name or fp
        key = f"{lib}:{name}"
        std = lib in ("Resistor_SMD", "Capacitor_SMD", "LED_SMD", "Diode_SMD",
                      "Package_TO_SOT_SMD", "Package_SO", "Connector_USB",
                      "Connector_PinHeader_2.54mm", "Fuse")
        got = kicad_mirror(lib, name) if std else None
        src = "kicad-mirror" if got else None
        if not got and lcsc and lcsc != "-":
            got = easyeda(lcsc, name)
            src = "easyeda" if got else None
            time.sleep(0.5)
        manifest[key] = {"wrl": (got or {}).get("wrl"), "step": (got or {}).get("step"),
                         "lcsc": lcsc, "mpn": mpn, "source": src or "missing"}
        print(f"{key[:52]:52} {src or 'missing'}")
    with open(os.path.join(ROOT, "3dmodels", "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    n = sum(1 for v in manifest.values() if v["source"] != "missing")
    print(f"DONE: {n}/{len(manifest)} footprints have 3D models")

if __name__ == "__main__":
    main()
