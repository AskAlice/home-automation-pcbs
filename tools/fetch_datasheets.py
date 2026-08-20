#!/usr/bin/env python3
"""fetch_datasheets.py — download datasheet PDFs for non-passive BOM parts.

Reads boards/*/bom_lcsc.csv, queries jlcsearch for direct PDF URLs
(wmsc.lcsc.com CDN), falls back to known manufacturer URLs. Writes
datasheets/<C#>_<MPN>.pdf + datasheets/manifest.json.
"""
import csv, glob, json, os, re, time, urllib.request

ROOT = "/mnt/agents/output/home-automation-pcbs"
OUT = os.path.join(ROOT, "datasheets")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

PASSIVE_FP = ("Resistor_SMD", "Capacitor_SMD", "LED_SMD")
SKIP_MPN = ("0603", "CL10A", "LTST-", "RC0603", "RMC0603", "RCA03")

# Manual fallback URLs for big-name parts (manufacturer-hosted)
FALLBACK = {
    "ESP32-C6-WROOM-1-N8": "https://www.espressif.com/sites/default/files/documentation/esp32-c6-wroom-1_datasheet_en.pdf",
    "ESP32-C3-WROOM-02-N4": "https://www.espressif.com/sites/default/files/documentation/esp32-c3-wroom-02_datasheet_en.pdf",
    "ESP32-S3-WROOM-1-N8": "https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_datasheet_en.pdf",
    "ESP32-H2-MINI-1": "https://www.espressif.com/sites/default/files/documentation/esp32-h2-mini-1_datasheet_en.pdf",
    "SHT31-DIS-B2.5kS": "https://www.sensirion.com/media/documents/213E6A3B/63A5A569/Datasheet_SHT3x_DIS.pdf",
    "SHT40-AD1B-R2": "https://www.sensirion.com/media/documents/33FD6951/662A593A/HT_DS_Datasheet_SHT4x.pdf",
    "SCD40-D-R2": "https://www.sensirion.com/media/documents/48C4B7FB/64C134E7/Sensirion_SCD4x_Datasheet.pdf",
    "SGP40-D-R4": "https://www.sensirion.com/media/documents/296373BB/6203E5E3/Sensirion_Gas_Sensors_SGP40_Datasheet.pdf",
    "BH1750FVI-TR": "https://www.mouser.com/datasheet/2/348/bh1750fvi-e-1868571.pdf",
    "BMP280": "https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp280-ds001.pdf",
    "AP2112K-3.3TRG1": "https://www.diodes.com/assets/Datasheets/AP2112.pdf",
    "AP63205WU-7": "https://www.diodes.com/assets/Datasheets/AP63200-AP63201-AP63203-AP63205.pdf",
    "MCP1700T-3302E/TT": "https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ProductDocuments/DataSheets/MCP1700-Data-Sheet-20001826F.pdf",
    "TMC2209-LA-T": "https://www.analog.com/media/en/technical-documentation/data-sheets/TMC2209_datasheet_rev1.09.pdf",
    "INMP441ACEZ-R7": "https://invensense.tdk.com/wp-content/uploads/2015/02/INMP441.pdf",
    "TSOP38238": "https://www.vishay.com/docs/82491/tsop382.pdf",
    "BL0942": "https://www.belling.com.cn/media/file_object/file_product/2021/12/01/bl0942_datasheet_en.pdf",
    "AO3400A": "https://www.vishay.com/docs/70655/70655.pdf",
    "AO3401A": "https://www.vishay.com/docs/70660/70660.pdf",
    "S8050": "https://www.mccsemi.com/pdf/Products/S8050(SOT-23).pdf",
    "1N4148WS": "https://www.vishay.com/docs/85746/1n4148ws.pdf",
    "PC817C-S": "https://www.sharpsma.com/download/PC817XxNSZ1B-epdf",
    "HLK-PM01": "https://hlktech.net/index.php?id=1188",
    "74AHCT125": "https://www.ti.com/lit/ds/symlink/sn74ahct125.pdf",
    "HLK-LD2410B": "https://hlktech.net/index.php?id=1091",
    "HLK-LD2450": "https://hlktech.net/index.php?id=1107",
}

def fetch(url, path):
    try:
        req = urllib.request.Request(url, headers=UA)
        data = urllib.request.urlopen(req, timeout=40).read()
        if data[:4] != b"%PDF" or len(data) < 10240:
            return False
        with open(path, "wb") as f:
            f.write(data)
        return True
    except Exception:
        return False

def jlcsearch_pdf(lcsc):
    try:
        url = f"https://jlcsearch.tscircuit.com/api/search?q={lcsc}&limit=3&full=true"
        req = urllib.request.Request(url, headers=UA)
        d = json.load(urllib.request.urlopen(req, timeout=30))
        for c in d.get("components", []):
            pdf = (c.get("extra") or {}).get("datasheet", {}).get("pdf")
            if pdf:
                return pdf
    except Exception:
        pass
    return None

def main():
    parts = {}
    for f in glob.glob(os.path.join(ROOT, "boards", "*", "bom_lcsc.csv")):
        with open(f) as fh:
            rows = list(csv.reader(fh))
        hdr = [h.strip().lower() for h in rows[0]]
        try:
            i_ref, i_val = hdr.index("ref"), hdr.index("value")
            i_fp = hdr.index("footprint"); i_lcsc = hdr.index("lcsc"); i_mpn = hdr.index("mpn")
        except ValueError:
            i_ref, i_val, i_fp, i_lcsc, i_mpn = 0, 1, 2, 3, 4
        for r in rows[1:]:
            if len(r) <= max(i_lcsc, i_mpn):
                continue
            lcsc, mpn, fp = r[i_lcsc].strip(), r[i_mpn].strip(), r[i_fp].strip()
            if not lcsc or lcsc == "-" or not mpn or mpn == "-":
                continue
            if any(fp.startswith(p) for p in PASSIVE_FP) or any(mpn.startswith(s) for s in SKIP_MPN):
                continue
            parts[lcsc] = (mpn, fp)
    manifest = []
    for lcsc, (mpn, fp) in sorted(parts.items()):
        safe = re.sub(r"[^\w.-]", "_", f"{lcsc}_{mpn}")[:80]
        path = os.path.join(OUT, safe + ".pdf")
        entry = {"lcsc": lcsc, "mpn": mpn, "footprint": fp, "file": None,
                 "url": None, "status": "pending"}
        if os.path.exists(path):
            entry.update(file=os.path.basename(path), status="cached")
            manifest.append(entry); continue
        url = jlcsearch_pdf(lcsc)
        ok = fetch(url, path) if url else False
        if not ok:
            for key, furl in FALLBACK.items():
                if key.lower() in mpn.lower() or mpn.lower() in key.lower():
                    ok = fetch(furl, path); url = furl if ok else url
                    break
        if not ok and mpn in FALLBACK:
            ok = fetch(FALLBACK[mpn], path); url = FALLBACK[mpn] if ok else url
        entry.update(file=os.path.basename(path) if ok else None,
                     url=url if ok else None,
                     status="fetched" if ok else "failed")
        manifest.append(entry)
        print(f"{lcsc:>10} {mpn[:32]:32} {entry['status']}")
        time.sleep(0.5)
    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    ok = sum(1 for e in manifest if e["status"] in ("fetched", "cached"))
    print(f"DONE: {ok}/{len(manifest)} datasheets")

if __name__ == "__main__":
    main()
