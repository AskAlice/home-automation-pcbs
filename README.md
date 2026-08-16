# home-automation-pcbs

Open-hardware IoT boards for home automation, designed for **ESPHome** and/or
**Matter-over-Thread / Zigbee** (ESP32-C3/C6/S3/H2 based). All projects are
native **KiCad 8** and fully self-contained (project-local symbol libraries,
inline custom footprints, generator scripts — every file is reproducible).

> ⚠ **Verify before fabrication.** Footprints for ESP modules and sensors are
> drawn from published datasheets but these boards have not been through a
> physical run. v0.1 boards have signal routing left for autorouting
> (documented per-board). Check each board README before ordering PCBs.
> **RelayMini contains mains voltage — read its safety section first.**

## Boards

| Board | MCU | Ecosystem | Function | Status |
|---|---|---|---|---|
| [`boards/sensenode-c6`](boards/sensenode-c6) | ESP32-C6-WROOM-1 | ESPHome (Wi-Fi) + Matter/Thread | Temp/hum, lux, pressure, PIR | v0.1 routed (power), partial ratsnest |
| [`boards/presencepro-c3`](boards/presencepro-c3) | ESP32-C3-WROOM-02 | ESPHome | HLK-LD2410 mmWave presence + lux | v0.1 |
| [`boards/ledquad-c3`](boards/ledquad-c3) | ESP32-C3-WROOM-02 | ESPHome / WLED | 4-ch 12–24 V PWM LED driver | v0.1 |
| [`boards/relaymini-c3`](boards/relaymini-c3) | ESP32-C3-WROOM-02 | ESPHome | ⚠ Mains switch + BL0942 metering | v0.1, safety gates green |
| [`boards/ledhub-c6`](boards/ledhub-c6) | ESP32-C6-WROOM-1 | WLED / ESPHome | 2.8" TFT all-in-one LED controller | v0.1 (flagship) |
| [`boards/threadnode-h2`](boards/threadnode-h2) | ESP32-H2-MINI-1 | Matter-over-Thread / Zigbee | Battery contact sensor / button | v0.1 concept |
| [`boards/airquality-s3`](boards/airquality-s3) | ESP32-S3-WROOM-1 | ESPHome | CO₂ + VOC + temp/hum + OLED header | v0.1 concept |
| [`boards/blinddriver-c6`](boards/blinddriver-c6) | ESP32-C6-WROOM-1 | ESPHome / Matter | TMC2209 roller-blind controller | v0.1 concept |
| [`boards/irblaster-c3`](boards/irblaster-c3) | ESP32-C3-WROOM-02 | ESPHome | IR TX/RX climate bridge | v0.1 concept |
| [`boards/gardenprobe-c6`](boards/gardenprobe-c6) | ESP32-C6-WROOM-1 | ESPHome / Matter | Battery soil-moisture probe | v0.1 concept |
| [`boards/threadrcp-h2`](boards/threadrcp-h2) | ESP32-H2-MINI-1 | OpenThread RCP / Zigbee NCP | Border-router USB dongle | v0.1 concept |

Each board folder contains: `*.kicad_pro/.kicad_sch/.kicad_pcb`, project-local
symbol library, `bom_lcsc.csv` (real, in-stock LCSC part numbers), `README.md`
(BOM, pinout, flashing, analyzer notes), `esphome/*.yaml`, render PNGs, and the
generator script (`gen_*.py`).

## Firmware

- `boards/*/esphome/*.yaml` — ready-to-adapt ESPHome configs.
- [`firmware/wled-usermod-ledhub`](firmware/wled-usermod-ledhub) — WLED usermod
  for LEDHub: ILI9341 status display, rotary encoder brightness, ADC-ladder
  nav buttons, LD2450 presence switching, SHT31/BH1750 telemetry.

## Part data

- [`datasheets/`](datasheets) — datasheet PDFs for all ICs/modules/connectors
  + `manifest.json` (re-sync: `python3 tools/fetch_datasheets.py`).
- [`3dmodels/`](3dmodels) — STEP + WRL models (EasyEDA/LCSC and KiCad
  packages3D mirror) referenced from every PCB (`${KIPRJMOD}/../../3dmodels/…`)
  + `manifest.json` (re-fetch: `python3 tools/fetch_3d.py`).

> **Note:** binary payloads (datasheet PDFs, STEP/WRL models, render PNGs) are
> not committed to git — they are fully regenerable: `tools/fetch_datasheets.py`,
> `tools/fetch_3d.py` (+ `tools/fix_3d.py`), and `tools/render_pcb.py` rebuild
> everything from the manifests in this repo.

## Tools

- `tools/kicadgen.py` — KiCad 8 s-expression writer + project validator used
  by every board generator (`python3 boards/<b>/gen_<b>.py` regenerates).
- `tools/render_pcb.py` — dependency-free PCB rasterizer (the render PNGs in
  each board folder).
- `tools/render3d.sh` — raytraced 3D renders (`render3d_top/bottom.png` per
  board) via `kicad-cli pcb render --quality high` (KiCad ≥ 9.0; use 10.0.0,
  9.0.9/10.0.1 drop component models in CLI renders — CPU raytracer, no X
  server needed).

## Design rules

2-layer, 1.6 mm, 0.2 mm clearance, 0.25 mm min track, ≥0.5 mm power tracks,
GND pour on B.Cu, antenna keepouts on all RF modules. Every board passes
[kicad-happy](https://github.com/aklofas/kicad-happy) schematic/PCB analysis
with zero cross-net violations (DFM-001 = 0); remaining warnings are triaged
in each board's README.

## Acknowledgements

Validation and datasheet tooling: [kicad-happy](https://github.com/aklofas/kicad-happy)
(MIT, © 2025 Andrew Klofas). 3D models: EasyEDA/LCSC and the KiCad official
packages3D libraries. ESP module footprints verified against
[espressif/kicad-libraries](https://github.com/espressif/kicad-libraries).

## License

MIT — see [LICENSE](LICENSE).
