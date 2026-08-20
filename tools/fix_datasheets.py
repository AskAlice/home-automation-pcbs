#!/usr/bin/env python3
"""fix_datasheets.py — curl-based retry for failed entries in datasheets/manifest.json."""
import json, os, re, subprocess, time

OUT = "/mnt/agents/output/home-automation-pcbs/datasheets"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
FALLBACK = {
    "SHT31": "https://www.sensirion.com/media/documents/213E6A3B/63A5A569/Datasheet_SHT3x_DIS.pdf",
    "SHT40": "https://www.sensirion.com/media/documents/33FD6951/662A593A/HT_DS_Datasheet_SHT4x.pdf",
    "SCD40": "https://www.sensirion.com/media/documents/48C4B7FB/64C134E7/Sensirion_SCD4x_Datasheet.pdf",
    "SGP40": "https://www.sensirion.com/media/documents/296373BB/6203E5E3/Sensirion_Gas_Sensors_SGP40_Datasheet.pdf",
    "ESP32-C6-WROOM-1": "https://www.espressif.com/sites/default/files/documentation/esp32-c6-wroom-1_datasheet_en.pdf",
    "ESP32-C3-WROOM-02": "https://www.espressif.com/sites/default/files/documentation/esp32-c3-wroom-02_datasheet_en.pdf",
    "ESP32-S3-WROOM-1": "https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_datasheet_en.pdf",
    "ESP32-H2-MINI-1": "https://www.espressif.com/sites/default/files/documentation/esp32-h2-mini-1_datasheet_en.pdf",
    "BMP280": "https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp280-ds001.pdf",
    "AP2112": "https://www.diodes.com/assets/Datasheets/AP2112.pdf",
    "AP63205": "https://www.diodes.com/assets/Datasheets/AP63200-AP63201-AP63203-AP63205.pdf",
    "TMC2209": "https://www.analog.com/media/en/technical-documentation/data-sheets/TMC2209_datasheet_rev1.09.pdf",
    "INMP441": "https://invensense.tdk.com/wp-content/uploads/2015/02/INMP441.pdf",
    "TSOP38238": "https://www.vishay.com/docs/82491/tsop382.pdf",
    "MCP1700": "https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ProductDocuments/DataSheets/MCP1700-Data-Sheet-20001826F.pdf",
    "AO3400": "https://www.vishay.com/docs/70655/70655.pdf",
    "AO3401": "https://www.vishay.com/docs/70660/70660.pdf",
}

def curl_pdf(url, path):
    try:
        r = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", "40",
                            "-o", path, url], capture_output=True)
        if r.returncode != 0:
            return False
        with open(path, "rb") as f:
            magic = f.read(4)
        return magic == b"%PDF" and os.path.getsize(path) > 10240
    except Exception:
        return False

def jlc_pdf(lcsc):
    try:
        r = subprocess.run(["curl", "-s", "-A", UA, "--max-time", "25",
                            f"https://jlcsearch.tscircuit.com/api/search?q={lcsc}&limit=3&full=true"],
                           capture_output=True)
        d = json.loads(r.stdout)
        for c in d.get("components", []):
            pdf = (c.get("extra") or {}).get("datasheet", {}).get("pdf")
            if pdf:
                return pdf
    except Exception:
        pass
    return None

def main():
    mp = os.path.join(OUT, "manifest.json")
    man = json.load(open(mp))
    fixed = 0
    for e in man:
        if e["status"] != "failed":
            continue
        lcsc, mpn = e.get("lcsc", ""), e.get("mpn", "")
        if not re.match(r"^C\d+$", lcsc or ""):
            continue  # parse artifact rows from odd CSVs
        safe = re.sub(r"[^\w.-]", "_", f"{lcsc}_{mpn}")[:80]
        path = os.path.join(OUT, safe + ".pdf")
        if os.path.exists(path):
            e.update(file=os.path.basename(path), status="ok")
            continue
        url = jlc_pdf(lcsc)
        ok = curl_pdf(url, path) if url else False
        if not ok:
            for key, furl in FALLBACK.items():
                if key.lower() in (mpn or "").lower():
                    ok = curl_pdf(furl, path); url = furl if ok else url
                    break
        if ok:
            e.update(file=os.path.basename(path), url=url, status="ok")
            fixed += 1
            print("FIXED", lcsc, mpn)
        time.sleep(0.4)
    json.dump(man, open(mp, "w"), indent=1)
    from collections import Counter
    print("fixed:", fixed, "final:", Counter(e["status"] for e in man))

if __name__ == "__main__":
    main()
