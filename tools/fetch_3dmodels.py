#!/usr/bin/env python3
"""Task 2: fetch 3D models (STEP+WRL) for every footprint used in boards/*/*.kicad_pcb.

- Custom footprints: easyeda2kicad --lcsc_id <C#> --full -> copy *.step/*.wrl
- Whitelisted KiCad footprints: raw.githubusercontent.com/KiCad/kicad-packages3D mirror
- Mechanical-only footprints (mounting holes, fiducials, copper probes): source "missing"
Output: 3dmodels/<Lib>.3dshapes/<Model>.{wrl,step} + 3dmodels/manifest.json
"""
import csv, glob, json, os, re, shutil, subprocess, sys, time, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "3dmodels")
UA = {"User-Agent": "Mozilla/5.0"}
MIRROR = "https://raw.githubusercontent.com/KiCad/kicad-packages3D/master/{lib}.3dshapes/{model}.{ext}"
SKIP_NAMES = {"MountingHole_M2.5", "Fiducial_1mm", "SoilProbe-BCu"}

def bom_lookup():
    """footprint-name (after colon) -> (lcsc, mpn). Prefer entries with a real LCSC."""
    m = {}
    for bom in glob.glob(os.path.join(REPO, "boards", "*", "bom_lcsc.csv")):
        with open(bom) as f:
            for row in csv.DictReader(f):
                row = {k.lower(): (v or "").strip() for k, v in row.items() if k}
                name = row["footprint"].split(":", 1)[-1]
                lcsc = row["lcsc"]
                if name not in m or (m[name][0] in ("-", "—", "") and lcsc not in ("-", "—", "")):
                    m[name] = (lcsc, row["mpn"])
    return m

def pcb_footprints():
    """set of 'lib:name' used across all PCBs"""
    s = set()
    for pcb in glob.glob(os.path.join(REPO, "boards", "*", "*.kicad_pcb")):
        txt = open(pcb).read()
        for m in re.finditer(r'\(footprint\s*\n?\s*"([^"]+)"', txt):
            s.add(m.group(1))
    return sorted(s)

def fetch(url, dest):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        if len(data) < 100:
            return False
        with open(dest, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"  fetch fail {url}: {e}", file=sys.stderr)
        return False

def easyeda(lcsc, workdir):
    """Return (step_path, wrl_path) from easyeda2kicad output or (None, None)."""
    shutil.rmtree(workdir, ignore_errors=True)
    try:
        r = subprocess.run(["easyeda2kicad", "--lcsc_id", lcsc, "--full",
                            "--output", workdir],
                           capture_output=True, text=True, timeout=180)
    except Exception as e:
        print(f"  easyeda2kicad {lcsc} error: {e}", file=sys.stderr)
        return None, None
    shapes = workdir + ".3dshapes"
    step = wrl = None
    if os.path.isdir(shapes):
        for f in os.listdir(shapes):
            if f.lower().endswith(".step"):
                step = os.path.join(shapes, f)
            elif f.lower().endswith(".wrl"):
                wrl = os.path.join(shapes, f)
    return step, wrl

def main():
    os.makedirs(OUT, exist_ok=True)
    bom = bom_lookup()
    manifest = {}
    done_custom = {}  # footprint name -> (lib, model) to dedupe across boards
    for fp in pcb_footprints():
        lib, name = fp.split(":", 1)
        lcsc, mpn = bom.get(name, ("-", ""))
        entry = {"lcsc": lcsc, "mpn": mpn, "wrl": None, "step": None, "source": "missing"}
        if name in SKIP_NAMES or not name:
            manifest[fp] = entry
            continue
        std_lib = lib.split("_")[0] in {"Resistor", "Capacitor", "LED", "Diode", "Fuse"} or \
                  lib.startswith(("Package_", "Connector_", "Fuse"))
        if std_lib:
            # KiCad packages3D mirror
            d = os.path.join(OUT, f"{lib}.3dshapes")
            os.makedirs(d, exist_ok=True)
            for ext, key in (("wrl", "wrl"), ("step", "step")):
                dest = os.path.join(d, f"{name}.{ext}")
                if os.path.exists(dest) or fetch(MIRROR.format(lib=lib, model=name, ext=ext), dest):
                    entry[key] = f"{lib}.3dshapes/{name}.{ext}"
            if entry["wrl"] or entry["step"]:
                entry["source"] = "kicad-mirror"
            manifest[fp] = entry
            time.sleep(0.3)
            continue
        # custom footprint -> easyeda by LCSC
        if name in done_custom:
            src_lib, model = done_custom[name]
            for key, ext in (("wrl", "wrl"), ("step", "step")):
                p = os.path.join(OUT, f"{src_lib}.3dshapes", f"{model}.{ext}")
                if os.path.exists(p):
                    entry[key] = f"{src_lib}.3dshapes/{model}.{ext}"
                    entry["source"] = "easyeda"
            manifest[fp] = entry
            continue
        if lcsc in ("-", "—", ""):
            manifest[fp] = entry  # unavailable
            continue
        tgt_lib = "Shared"
        step, wrl = easyeda(lcsc, f"/tmp/e2k_{lcsc}")
        if step or wrl:
            d = os.path.join(OUT, f"{tgt_lib}.3dshapes")
            os.makedirs(d, exist_ok=True)
            if wrl:
                shutil.copy(wrl, os.path.join(d, f"{name}.wrl"))
                entry["wrl"] = f"{tgt_lib}.3dshapes/{name}.wrl"
            if step:
                shutil.copy(step, os.path.join(d, f"{name}.step"))
                entry["step"] = f"{tgt_lib}.3dshapes/{name}.step"
            entry["source"] = "easyeda"
            done_custom[name] = (tgt_lib, name)
        manifest[fp] = entry
        print(f"{fp}: {entry['source']}", file=sys.stderr)
        time.sleep(0.3)
    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    srcs = {}
    for e in manifest.values():
        srcs[e["source"]] = srcs.get(e["source"], 0) + 1
    print("DONE", srcs, file=sys.stderr)

if __name__ == "__main__":
    main()
