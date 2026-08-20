# airquality-s3 — CO2/VOC/temp/humidity node (SPEC 7.2)

ESP32-S3-WROOM-1 air-quality monitor: SCD40 (CO2), SGP40 (VOC), SHT40
(temp/hum) on one I2C bus, SSD1306 OLED header, USB-C power + flashing.
**v0.1 concept board.**

- Board: 60 × 40 mm, 2-layer, USB-C bottom edge, antenna keep-out top-left
- Power: USB 5 V → AP2112K-3.3 LDO
- Status: `python3 boards/wave2/wave2gen.py airquality-s3` → self-check OK

## BOM (bom_lcsc.csv)

| Ref | Value | Footprint | LCSC # | MPN | Qty |
|---|---|---|---|---|---|
| U1 | ESP32-S3-WROOM-1-N8 | ESP32-S3-WROOM-1 | C2913201 | ESP32-S3-WROOM-1-N8 | 1 |
| U2 | AP2112K-3.3 | SOT-23-5 | C51118 | AP2112K-3.3TRG1 | 1 |
| U3 | SCD40 | custom:SCD40-SMD | C144956 | SCD40-D-R2 | 1 |
| U4 | SGP40 | custom:SGP40-DFN6 | C2905033 | SGP40-D-R4 | 1 |
| U5 | SHT40-AD1B | custom:SHT4x-DFN4 | C2685600 | SHT40-AD1B-R2 | 1 |
| X1 | USB-C 16P | custom:USB-C-16P-MidMount | C165948 | TYPE-C-31-M-12 | 1 |
| BT1,BT2 | SW_PUSH (BOOT / RST) | custom:Tactile-6x6-SMD | C91808 | TS-1187A-B-A-B | 2 |
| D1 | LED red (STAT) | 0603 | C2286 | 17-21SURC/S530-A3/TR8 | 1 |
| R1,R2 | 4.7k (I2C pull-ups) | 0603 | C23162 | 0603WAF4701T5E | 2 |
| R3,R4 | 5.1k (USB CC1/CC2) | 0603 | C23186 | 0603WAF5101T5E | 2 |
| R7 | 10k (EN) | 0603 | C98252 | 0603WAF1002T5E | 1 |
| R8 | 1k (LED) | 0603 | C21190 | 0603WAF1001T5E | 1 |
| C1,C2,C3,C4 | 100nF | 0603 | C14663 | CL10B104KB8NNNC | 4 |
| C5 | 10uF | 0805 | C15850 | CL21A106KPFNNNE | 1 |
| J1 | Conn_01x04 (3V3/TX0/RX0/GND) | PinHeader_1x04_P2.54mm | C49241 | A2541WV-4P | 1 |
| J2 | Conn_01x04 (3V3/SDA/SCL/GND, OLED) | PinHeader_1x04_P2.54mm | C49241 | A2541WV-4P | 1 |

## Pinout (S3-WROOM-1)

| Signal | GPIO | Notes |
|---|---|---|
| I2C_SDA / I2C_SCL | GPIO8 / GPIO9 | R1/R2 4.7k pull-ups; SCD40 0x62, SGP40 0x59, SHT40 0x44, OLED 0x3C |
| BOOT | GPIO0 | BT1 button |
| RST | EN | BT2 button |
| STAT_LED | GPIO38 | D1 via R8 |
| USB D- / D+ | GPIO19 / GPIO20 | native USB-Serial-JTAG flashing |
| TX0 / RX0 | GPIO43 / GPIO44 | J1 spare UART header |

## Firmware

See `esphome/airquality-s3.yaml` — scd4x + sgp40 + sht4x sensors, SSD1306
display on J2, status LED, BOOT button.

## Routing status

**v0.1 concept — signals left for autorouting.** Power rails routed
(VBUS/+3V3/GND with vias + stitching); I2C/UART/USB/sensor signals unrouted.

## Analyzer notes

`analyze_pcb.py`: **DFM-001 = 0**. RT-001 unrouted errors expected
(autoroute deferred). Buttons rotated 90° on the left edge to clear the
module pad columns.

## Caveats (verify before fabrication!)

- SCD40 self-heating skews SHT40 readings — keep sensor spacing / consider
  SCD40 periodic-measurement mode; verify thermal layout before fab.
- USB CC resistors R3/R4 = 5.1k required for USB-C host detection.
- **Verify all footprints, pin numbers, and clearances against KiCad
  libraries + datasheets before ordering boards.**

## Renders

| Raytraced 3D (KiCad) | 2D layout |
|---|---|
| ![top](render3d_top.png) | ![top](render_top.png) |
| ![bottom](render3d_bottom.png) | ![bottom](render_bottom.png) |
