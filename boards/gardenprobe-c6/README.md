# gardenprobe-c6 — battery soil-moisture stick node (SPEC 7.5)

ESP32-C6-WROOM-1 soil-probe node: 70 × 25 mm stick with capacitive copper
probe area on the B.Cu tip (J2), JST-PH LiPo input, MCP1700-3302 LDO,
AO3401 sensor-rail load switch, SHT31 temp/humidity, battery divider.
**v0.1 concept board.**

- Board: 70 × 25 mm, 2-layer; antenna keep-out along left edge; probe tip right
- Power: 3.7 V LiPo on JST-PH (BT1) — **charge externally, no charger on board**
- Status: `python3 boards/wave2/wave2gen.py gardenprobe-c6` → self-check OK

## BOM (bom_lcsc.csv)

| Ref | Value | Footprint | LCSC # | MPN | Qty |
|---|---|---|---|---|---|
| U1 | ESP32-C6-WROOM-1 (rot 270°) | ESP32-C6-WROOM-1 | C2946979 | ESP32-C6-WROOM-1-N8 | 1 |
| U2 | MCP1700-3302E | SOT-23 | C63395 | MCP1700T-3302E/TT | 1 |
| U3 | SHT31-DIS | custom:SHT31-DFN8 | C23324 | SHT31-DIS-B2.5kS | 1 |
| Q1 | AO3401 (load switch) | SOT-23 | C15127 | AO3401A | 1 |
| BT1 | JST-PH 2P (LiPo) | custom:JST-PH-S2B | C265758 | S2B-PH-K-S | 1 |
| J2 | SoilProbe electrodes | custom:SoilProbe-BCu | — | copper area on B.Cu (ENIG rec.) | 1 |
| R1,R4 | 100k (battery divider) | 0603 | C98258 | 0603WAF1003T5E | 2 |
| R5 | 1M (soil charge) | 0603 | C22935 | 0603WAF1004T5E | 1 |
| R3 | 10k (load-switch gate) | 0603 | C98252 | 0603WAF1002T5E | 1 |
| R6,R7 | 4.7k (I2C pull-ups, switched) | 0603 | C23162 | 0603WAF4701T5E | 2 |
| C1,C2,C3,C4 | 100nF | 0603 | C14663 | CL10B104KB8NNNC | 4 |
| J1 | Conn_01x04 (3V3/TX0/RX0/GND) | PinHeader_1x04_P2.54mm | C49241 | A2541WV-4P | 1 |

## Pinout (C6-WROOM-1)

| Signal | GPIO | Notes |
|---|---|---|
| SOIL_ADC | GPIO0 | probe sense via R5 1M from GPIO1 (fixed-RC) |
| SOIL_CHG | GPIO1 | charge/drive pin for probe |
| BATT_ADC | GPIO2 | 100k/100k divider → Vbat/2 |
| LOAD_EN | GPIO3 | Q1 AO3401 → +3V3_SW (SHT31 + I2C pull-ups) |
| I2C_SDA / I2C_SCL | GPIO20 / GPIO21 | U3 SHT31 (0x44), pull-ups on switched rail |
| TX0 / RX0 | GPIO16 / GPIO17 | J1 prog header (flash via UART; no USB) |
| EN | — | pull-up + C2 |

## Firmware

See `esphome/gardenprobe-c6.yaml` — load-switch GPIO3, sht3xd on switched
I2C, ADC soil raw (GPIO0) + battery (GPIO2, ×2), deep-sleep 30 min cycles.
Calibrate soil raw → % per installation.

## Routing status

**v0.1 concept — signals left for autorouting.** Power rails routed
(VBAT/+3V3/+3V3_SW/GND + stitching); ADC/I2C/UART/enable signals unrouted.

## Analyzer notes

`analyze_pcb.py`: **DFM-001 = 0**. RT-001 unrouted errors expected.
SHT31 DFN-8 EP resized (1.4×1.0) to clear the 1.05 mm pad columns.

## Caveats (verify before fabrication!)

- No battery charger on board — LiPo must be charged externally; consider
  adding protection (DW01) for production.
- Probe electrodes are bare B.Cu — specify ENIG or immersion-gold finish;
  HASL/copper will corrode in soil quickly.
- MCP1700 Iq ~1.6 µA suits sleep; verify divider current budget (100k/100k
  ≈ 21 µA at 4.2 V — the dominant sleep draw; raise values if needed).
- **Verify all footprints, pin numbers, and clearances against KiCad
  libraries + datasheets before ordering boards.**

## Renders

| Raytraced 3D (KiCad) | 2D layout |
|---|---|
| ![top](https://www.kimi.com/apiv2-files/sign-obj/kimi-fs%2Ffiles%2Fblob%2F3acfabcea5a765ea5bc1c849cf162f617ae7ce632e19d1cd123c0edbc4772fbd?filename=render3d_top.png&sig=C6MKLdjD0rUvBoR9Grd7L-g9ULDs94t9Vjv3VyegZqo=&t=o) | ![top](https://www.kimi.com/apiv2-files/sign-obj/kimi-fs%2Ffiles%2Fblob%2Feea8292abb51e6c4a41932cfde0d4746f672ed2528fa8f47f6494b0460b9d0d8?filename=render_top.png&sig=VlqcPloSoB5wbslgUvI_DCrczMQiCzGrim_5Ydsi244=&t=o) |
| ![bottom](https://www.kimi.com/apiv2-files/sign-obj/kimi-fs%2Ffiles%2Fblob%2F1c19e01aba41671237374c43cfc1a4947b9ff48aaad5db58657ed8cfac2d9b97?filename=render3d_bottom.png&sig=xqZkDLVsjLnOiR9nt6vMe7tk7pqL2E9XZ1NcMhbLZOU=&t=o) | ![bottom](https://www.kimi.com/apiv2-files/sign-obj/kimi-fs%2Ffiles%2Fblob%2F5b265f8ba35bdbd72fc9599d7a89278f1e71b1303a1cd8de31e92c8a61c43ce8?filename=render_bottom.png&sig=4sp0EouFGp0xv1UzX4dRanP5TPeIP8RWCz-6KA62_q4=&t=o) |

🎬 [360° turntable video](https://www.kimi.com/apiv2-files/sign-obj/kimi-fs%2Ffiles%2Fblob%2F4ac2e2f323faa94b68d611f76236c4973d634755f8f55330ad2cb576df0b9c13?filename=turntable.gif&sig=bwavthwIY5KeNMsptGdtvxAUFDBq8hS3c6cDmvnCd7Q=&t=o) — 24 real KiCad raytraced frames stitched with ffmpeg (tools/turntable.sh).
