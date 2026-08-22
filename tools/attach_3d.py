#!/usr/bin/env python3
"""attach_3d.py — fetch 3D models and attach one to every footprint.

    python3 tools/attach_3d.py            # fetch missing models, patch PCBs
    python3 tools/attach_3d.py --refetch  # re-download everything

MODELS maps a footprint name (the part after "lib:") to where its body comes
from.  Each source also provides a reference footprint (.kicad_mod) whose
(model …) block gives the offset/rotation that aligns the body with *that*
footprint; we re-centre it on this repo's footprint by comparing pad
bounding boxes, so the generated (custom:…) footprints line up too.

Sources
  ("kicad", "<Lib>", "<Name>")     KiCad packages3D / kicad-footprints (GitHub)
  ("espressif", "<Name>", "<ext>") espressif/kicad-libraries (GitHub)
  ("lcsc", "C123456")              EasyEDA via easyeda2kicad (pip)
  None                             no body (holes, fiducials, copper-only)

Model files land in 3dmodels/<Lib>.3dshapes/ (not committed — regenerable);
3dmodels/manifest.json records the resolved path + transform per footprint.
Every (model …) block in every board is rebuilt from scratch, so the script
is idempotent and safe to re-run after a board is regenerated.
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(ROOT, "3dmodels")
MANIFEST = os.path.join(MODELS_DIR, "manifest.json")
UA = {"User-Agent": "Mozilla/5.0 home-automation-pcbs/attach_3d"}

KICAD_3D = "https://raw.githubusercontent.com/KiCad/kicad-packages3D/master/{lib}.3dshapes/{name}.{ext}"
KICAD_FP = "https://raw.githubusercontent.com/KiCad/kicad-footprints/master/{lib}.pretty/{name}.kicad_mod"
ESP_3D = "https://raw.githubusercontent.com/espressif/kicad-libraries/main/3dmodels/espressif.3dshapes/{name}.{ext}"
ESP_FP = "https://raw.githubusercontent.com/espressif/kicad-libraries/main/footprints/Espressif.pretty/{name}.kicad_mod"

K, E, L = "kicad", "espressif", "lcsc"
MODELS = {
    # passives
    "R_0603_1608Metric": (K, "Resistor_SMD", "R_0603_1608Metric"),
    "Shunt-2512": (K, "Resistor_SMD", "R_2512_6332Metric"),
    "C_0603_1608Metric": (K, "Capacitor_SMD", "C_0603_1608Metric"),
    "C_0805_2012Metric": (K, "Capacitor_SMD", "C_0805_2012Metric"),
    "CP_Electrolytic_5x5.3": (K, "Capacitor_SMD", "CP_Elec_5x5.3"),
    "LED_0603_1608Metric": (K, "LED_SMD", "LED_0603_1608Metric"),
    "IND-4040": (L, "C167874"),
    "L-4x4-4R7": (L, "C167874"),
    "MOV-10D": (K, "Varistor", "RV_Disc_D12mm_W3.9mm_P7.5mm"),
    "Fuse_1206_3216Metric": (K, "Fuse", "Fuse_1206_3216Metric"),
    # semiconductors
    "SOT-23": (K, "Package_TO_SOT_SMD", "SOT-23"),
    "SOT-23-5": (K, "Package_TO_SOT_SMD", "SOT-23-5"),
    "SOT-23-6": (K, "Package_TO_SOT_SMD", "SOT-23-6"),
    "SOIC-14_3.9x8.7mm_P1.27mm": (K, "Package_SO", "SOIC-14_3.9x8.7mm_P1.27mm"),
    "D_SMA": (K, "Diode_SMD", "D_SMA"),
    "D_SOD-323": (K, "Diode_SMD", "D_SOD-323"),
    "PC817-SOP4": (L, "C3008369"),
    "BL0942-SSOP10": (L, "C2837510"),
    "IR-LED-5mm": (K, "LED_THT", "LED_D5.0mm_IRBlack"),
    "TSOP38238": (L, "C141632"),
    # sensors
    "BH1750-WSOF6": (L, "C78960"),
    "BMP280-LGA8": (K, "Package_LGA", "Bosch_LGA-8_2x2.5mm_P0.65mm_ClockwisePinNumbering"),
    "SHT31-DFN8": (L, "C80862"),
    "SHT40-DFN4": (L, "C2909890"),
    "SGP40-DFN6": (L, "C2874215"),
    "SCD40": (L, "C3659421"),
    "INMP441-LGA9": (L, "C2682118"),
    "Reed-SMD": (L, "C315909"),
    # modules
    "ESP32-C3-WROOM-02": (E, "ESP32-C3-WROOM-02", "STEP"),
    "ESP32-C6-WROOM-1": (E, "ESP32-C6-WROOM-1", "STEP"),
    "ESP32-S3-WROOM-1": (E, "ESP32-S3-WROOM-1", "STEP"),
    "ESP32-H2-MINI-1": (E, "ESP32-H2-MINI-1", "STEP"),
    "HLK-PM01": (L, "C209903"),
    "HF32F-G": (L, "C74541"),
    # connectors / electromechanical
    "USB_C_Receptacle_USB2.0_16P": (L, "C165948"),
    "PinHeader_1x03_P2.54mm_Vertical": (K, "Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical"),
    "PinHeader_1x04_P2.54mm_Vertical": (K, "Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Vertical"),
    "PinHeader_1x05_P2.54mm_Vertical": (K, "Connector_PinHeader_2.54mm", "PinHeader_1x05_P2.54mm_Vertical"),
    "PinHeader_1x08_P2.54mm_Vertical": (K, "Connector_PinHeader_2.54mm", "PinHeader_1x08_P2.54mm_Vertical"),
    "PinHeader_2x07_P2.54mm_Vertical": (K, "Connector_PinHeader_2.54mm", "PinHeader_2x07_P2.54mm_Vertical"),
    "JST-PH-2": (K, "Connector_JST", "JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical"),
    "KF128-5.08-2P": (L, "C474952"),
    "TB-5.08-2P": (L, "C474952"),
    "ScrewTerm-5.08-2P": (L, "C474952"),
    "TerminalBlock-5.08-2P": (L, "C8465"),
    "KF128-5.08-3P": (L, "C474953"),
    "TB-5.08-5P": (L, "C42377750"),
    "Tactile-6x6-SMD": (L, "C139797"),
    "EC11-Encoder": (L, "C370970"),
    "CR2032-holder": (L, "C5239862"),
    # no body
    "FuseClip-5x20": None,  # bare 20 mm-pitch clips; every library holder is a 31 mm housing
    "MountingHole_M2.5": None,
    "Fiducial_1mm": None,
    "SoilProbe-BCu": None,
}

# Hand overrides applied after the automatic alignment: footprint -> dict with
# any of offset=(x,y,z) rotate=(x,y,z) (absolute values, mm / degrees).
OVERRIDES = {}


# ------------------------------------------------------------------ s-expr
def match_paren(s, i):
    """Index of the ')' closing the '(' at s[i] (string-aware)."""
    depth, in_str = 0, False
    for j in range(i, len(s)):
        c = s[j]
        if c == '"' and s[j - 1] != "\\":
            in_str = not in_str
        elif not in_str:
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return j
    raise ValueError("unbalanced s-expression")


def blocks(txt, head):
    """Yield (start, end) of every '(head …)' block, outermost first."""
    for m in re.finditer(r"\(%s(?=[\s(])" % re.escape(head), txt):
        yield m.start(), match_paren(txt, m.start())


def pad_bbox(body):
    """Bounding box of all pads (footprint-local mm) or None."""
    xs, ys = [], []
    for s, e in blocks(body, "pad"):
        pad = body[s:e]
        at = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)", pad)
        size = re.search(r"\(size\s+([-\d.]+)\s+([-\d.]+)", pad)
        if not (at and size):
            continue
        x, y = float(at.group(1)), float(at.group(2))
        w, h = float(size.group(1)) / 2, float(size.group(2)) / 2
        xs += [x - w, x + w]
        ys += [y - h, y + h]
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def model_xform(body):
    """(offset, rotate, scale) from the first (model …) block, default identity."""
    out = {"offset": (0.0, 0.0, 0.0), "rotate": (0.0, 0.0, 0.0), "scale": (1.0, 1.0, 1.0)}
    for s, e in blocks(body, "model"):
        blk = body[s:e]
        for key in out:
            m = re.search(r"\(%s\s*\(xyz\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)" % key, blk)
            if m:
                out[key] = tuple(float(v) for v in m.groups())
        break
    return out


# ------------------------------------------------------------------ fetch
def download(url, path, min_bytes=200):
    if os.path.exists(path):
        return True
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
    except Exception as exc:  # noqa: BLE001
        print(f"    ! {url}: {exc}")
        return False
    if len(data) < min_bytes:
        return False
    with open(path, "wb") as fh:
        fh.write(data)
    return True


def easyeda2kicad():
    exe = shutil.which("easyeda2kicad")
    if exe:
        return [exe]
    try:
        subprocess.run([sys.executable, "-c", "import easyeda2kicad"], check=True,
                       capture_output=True)
    except subprocess.CalledProcessError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "easyeda2kicad"],
                       check=True)
    return [sys.executable, "-m", "easyeda2kicad"]


def fetch(src, refetch):
    """Return (model_relpath, reference_kicad_mod_text) or (None, None)."""
    kind = src[0]
    if kind == K:
        _, lib, name = src
        d = os.path.join(MODELS_DIR, f"{lib}.3dshapes")
        wrl = os.path.join(d, f"{name}.wrl")
        ref = os.path.join(d, f"{name}.kicad_mod")
        if refetch:
            for p in (wrl, ref):
                if os.path.exists(p):
                    os.remove(p)
        if not download(KICAD_3D.format(lib=lib, name=name, ext="wrl"), wrl):
            return None, None
        download(KICAD_3D.format(lib=lib, name=name, ext="step"), os.path.join(d, f"{name}.step"))
        download(KICAD_FP.format(lib=lib, name=name), ref)
        return os.path.relpath(wrl, MODELS_DIR), open(ref).read() if os.path.exists(ref) else ""
    if kind == E:
        _, name, ext = src
        d = os.path.join(MODELS_DIR, "espressif.3dshapes")
        mdl = os.path.join(d, f"{name}.{ext}")
        ref = os.path.join(d, f"{name}.kicad_mod")
        if refetch:
            for p in (mdl, ref):
                if os.path.exists(p):
                    os.remove(p)
        if not download(ESP_3D.format(name=name, ext=ext), mdl):
            return None, None
        download(ESP_FP.format(name=name), ref)
        return os.path.relpath(mdl, MODELS_DIR), open(ref).read() if os.path.exists(ref) else ""
    if kind == L:
        _, lcsc = src
        d = os.path.join(MODELS_DIR, "LCSC.3dshapes")
        wrl = os.path.join(d, f"{lcsc}.wrl")
        ref = os.path.join(d, f"{lcsc}.kicad_mod")
        if not refetch and os.path.exists(wrl) and os.path.exists(ref):
            return os.path.relpath(wrl, MODELS_DIR), open(ref).read()
        os.makedirs(d, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "e2k")
            for attempt in range(4):  # EasyEDA 403s bursts of requests
                time.sleep(1.5 * (1 + 3 * attempt))
                r = subprocess.run(easyeda2kicad() + ["--lcsc_id", lcsc, "--full", "--overwrite",
                                                      "--output", out],
                                   capture_output=True, text=True, timeout=180)
                shapes = glob.glob(os.path.join(tmp, "e2k.3dshapes", "*"))
                mods = glob.glob(os.path.join(tmp, "e2k.pretty", "*.kicad_mod"))
                if (shapes and mods) or "403" not in r.stdout + r.stderr:
                    break
            if not shapes or not mods:
                print(f"    ! easyeda2kicad {lcsc}: {(r.stderr or r.stdout).strip()[-200:]}")
                return None, None
            for f in shapes:
                ext = f.rsplit(".", 1)[-1].lower()
                if ext in ("wrl", "step"):
                    shutil.copy(f, os.path.join(d, f"{lcsc}.{ext}"))
            shutil.copy(mods[0], ref)
        if not os.path.exists(wrl):
            return None, None
        return os.path.relpath(wrl, MODELS_DIR), open(ref).read()
    raise ValueError(src)


# ------------------------------------------------------------------ align
def align(ref_mod, repo_body):
    """Transform that places the reference model on the repo footprint.

    Starts from the reference footprint's own (model …) transform and shifts
    it by the difference between the two pad bounding-box centres (KiCad model
    offsets use +Y up, board coordinates use +Y down).  If one footprint is
    clearly landscape and the other portrait, the model is turned 90°.
    """
    x = model_xform(ref_mod)
    rb, pb = pad_bbox(ref_mod), pad_bbox(repo_body)
    off, rot = list(x["offset"]), list(x["rotate"])
    note = ""
    if rb and pb:
        rw, rh = rb[2] - rb[0], rb[3] - rb[1]
        pw, ph = pb[2] - pb[0], pb[3] - pb[1]
        rcx, rcy = (rb[0] + rb[2]) / 2, (rb[1] + rb[3]) / 2
        if max(rw, rh) > 1.3 * min(rw, rh) and (rw > rh) != (pw > ph):
            rot[2] = (rot[2] + 90) % 360
            rcx, rcy = -rcy, rcx  # reference centre after the same turn
            note = " rot90"
        dx, dy = (pb[0] + pb[2]) / 2 - rcx, (pb[1] + pb[3]) / 2 - rcy
        if abs(dx) > 0.05 or abs(dy) > 0.05:
            off[0] += dx
            off[1] -= dy
            note += f" shift({dx:+.2f},{dy:+.2f})"
    return {"offset": [round(v, 3) for v in off], "rotate": [round(v, 3) for v in rot],
            "scale": list(x["scale"])}, note


# ------------------------------------------------------------------ patch
def model_block(rel, xf, indent="    "):
    i2 = indent + "  "
    f = lambda v: " ".join(f"{c:g}" for c in v)
    return (f"\n{indent}(model \"${{KIPRJMOD}}/../../3dmodels/{rel}\"\n"
            f"{i2}(offset (xyz {f(xf['offset'])}))\n"
            f"{i2}(scale (xyz {f(xf['scale'])}))\n"
            f"{i2}(rotate (xyz {f(xf['rotate'])}))\n"
            f"{indent})")


def strip_models(body):
    """Remove every (model …) block from a footprint body."""
    out, pos = [], 0
    for s, e in blocks(body, "model"):
        if s < pos:
            continue
        # also eat the whitespace run before the block
        ws = s
        while ws > pos and body[ws - 1] in " \t\r\n":
            ws -= 1
        out.append(body[pos:ws])
        pos = e + 1
    out.append(body[pos:])
    return "".join(out)


def footprint_name(body):
    m = re.match(r'\(footprint\s+"([^"]+)"', body)
    return m.group(1).split(":")[-1] if m else None


def patch_pcb(pcb, resolved):
    """Rebuild model blocks; returns (attached, missing-names)."""
    txt = open(pcb).read()
    out, pos, n, missing = [], 0, 0, set()
    for s, e in blocks(txt, "footprint"):
        body = strip_models(txt[s:e])
        name = footprint_name(body)
        if name not in MODELS:
            missing.add(name)
        entry = resolved.get(name)
        if entry:  # body excludes the footprint's closing paren
            body = body.rstrip() + model_block(entry["model"], entry) + "\n  "
            n += 1
        out.append(txt[pos:s])
        out.append(body)
        pos = e
    out.append(txt[pos:])
    new = "".join(out)
    if new != txt:
        with open(pcb, "w") as fh:
            fh.write(new)
    return n, missing


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--refetch", action="store_true", help="re-download all models")
    args = ap.parse_args()

    pcbs = sorted(glob.glob(os.path.join(ROOT, "boards", "*", "*.kicad_pcb")))
    # first repo footprint body per name (for pad-bbox alignment)
    repo_fp = {}
    for pcb in pcbs:
        txt = open(pcb).read()
        for s, e in blocks(txt, "footprint"):
            body = txt[s:e]
            repo_fp.setdefault(footprint_name(body), body)

    resolved, failed = {}, []
    for name in sorted(MODELS):
        src = MODELS[name]
        if src is None or name not in repo_fp:
            continue
        rel, ref = fetch(src, args.refetch)
        if not rel:
            failed.append(name)
            print(f"  {name:34} MISSING ({src})")
            continue
        xf, note = align(ref, repo_fp[name])
        for key, val in OVERRIDES.get(name, {}).items():
            xf[key] = list(val)
        resolved[name] = {"source": src[0], "model": rel, "lcsc": src[1] if src[0] == L else None,
                          **xf}
        print(f"  {name:34} {rel}{note}")

    with open(MANIFEST, "w") as fh:
        json.dump(resolved, fh, indent=1, sort_keys=True)

    unknown = set()
    for pcb in pcbs:
        n, missing = patch_pcb(pcb, resolved)
        unknown |= missing
        print(f"{os.path.basename(pcb):28} {n} models")
    if unknown:
        print("footprints without a MODELS entry:", ", ".join(sorted(unknown)))
    if failed:
        print("models that could not be fetched:", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
