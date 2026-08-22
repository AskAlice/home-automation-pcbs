# blinddriver-c6 — TMC2209 roller-blind controller (SPEC 7.3)

ESP32-C6-WROOM-1 driving a TMC2209 stepper socket for a roller blind:
12 V VMOT input (SS34 reverse-polarity protection), AP63205 buck to 5 V,
AP2112 to 3.3 V, screw terminals for motor + VMOT, end-stop header.
**v0.1 concept board.**

- Board: 60 × 40 mm, 2-layer, USB-C bottom edge
- Status: `python3 boards/wave2/wave2gen.py blinddriver-c6` → self-check OK

## BOM (bom_lcsc.csv)

| Ref | Value | Footprint | LCSC # | MPN | Qty |
|---|---|---|---|---|---|
| U1 | ESP32-C6-WROOM-1 | ESP32-C6-WROOM-1 | C2946979 | ESP32-C6-WROOM-1-N8 | 1 |
| U2 | AP63205 (buck 12V→5V) | SOT-23-6 | C2677326 | AP63205WU-7 | 1 |
| U3 | AP2112K-3.3 | SOT-23-5 | C51118 | AP2112K-3.3TRG1 | 1 |
| U4 | TMC2209 module | custom:TMC2209-Socket (J3/J4) | C3137092 | TMC2209 | 1 |
| L1 | 4.7uH | custom:Inductor-4x4 | C424814 | SWPA4026S4R7MT | 1 |
| D1 | LED red (STAT) | 0603 | C2286 | 17-21SURC/S530-A3/TR8 | 1 |
| D2 | SS34 (VMOT reverse pol.) | SMA | C14936 | SS34 | 1 |
| D3 | SS34 (buck catch) | SMA | C14936 | SS34 | 1 |
| X1 | USB-C 16P | custom:USB-C-16P-MidMount | C165948 | TYPE-C-31-M-12 | 1 |
| BT1,BT2 | SW_PUSH (BOOT / RST) | custom:Tactile-6x6-SMD | C91808 | TS-1187A-B-A-B | 2 |
| R8 | 1k | 0603 | C21190 | 0603WAF1001T5E | 1 |
| R1,R2,R9 | 5.1k (CC/USB) | 0603 | C23186 | 0603WAF5101T5E | 3 |
| R3,R4 | 22R (USB series) | 0603 | C25076 | 0603WAF220JT5E | 2 |
| R7 | 10k (EN) | 0603 | C98252 | 0603WAF1002T5E | 1 |
| R10,R11 | 100k (buck FB) | 0603 | C98258 | 0603WAF1003T5E | 2 |
| C1–C7 | 100nF | 0603 | C14663 | CL10B104KB8NNNC | 7 |
| C8 | 100uF (VMOT bulk) | custom:CP-Elec-6.3x5.4 | C145465 | RVT1H101M0607 | 1 |
| J5 | VMOT_IN screw 1x02 | custom:ScrewTerm-5.08-2P | C8464 | KF128-5.08-2P | 1 |
| J6,J7 | MOT_A / MOT_B screw 1x02 | custom:ScrewTerm-5.08-2P | C8464 | KF128-5.08-2P | 2 |
| J8 | Conn_01x03 (3V3/ENDSTOP/GND) | PinHeader_1x03_P2.54mm | C49240 | A2541WV-3P | 1 |

## Pinout (C6-WROOM-1)

| Signal | GPIO | Notes |
|---|---|---|
| STEP / DIR | GPIO4 / GPIO5 | to TMC2209 socket |
| TMC_EN | GPIO6 | low = driver enabled |
| DIAG | GPIO7 | TMC2209 diagnostic output |
| TMC_UART | GPIO15 | 1-wire UART config (PDN_UART) |
| ENDSTOP | GPIO18 | J8 header, pull-up |
| STAT_LED | GPIO1 | D1 via R8 |
| BOOT | GPIO0 | BT1; RST = EN (BT2) |
| USB D- / D+ | GPIO12 / GPIO13 | via 22R R3/R4, native USB flashing |
| TX0 / RX0 | GPIO16 / GPIO17 | spare |

## Firmware

See `esphome/blinddriver-c6.yaml` — stepdir stepper + time_based cover,
end-stop binary sensor, driver-enable switch, TMC2209 UART note.

## Routing status

**v0.1 concept — signals left for autorouting.** Power rails routed
(VMOT/12V/+5V/+3V3/GND, 0.5 mm power width, GND stitching); STEP/DIR/UART/
DIAG/end-stop signals unrouted.

## Analyzer notes

`analyze_pcb.py`: **DFM-001 = 0**. RT-001 unrouted errors expected.
STAT_LED was unassigned in the original plan — now on GPIO1.

## Caveats (verify before fabrication!)

- 12 V VMOT: check SS34 orientation (D2 input, D3 buck catch) and C8
  ripple rating for your motor current.
- TMC2209 socket pinout follows the common StepStick order — verify
  against your module (there are two header orientations).
- Buck feedback R10/R11 100k/100k sets 5 V via AP63205 reference — verify
  ratio against datasheet before fab.
- **Verify all footprints, pin numbers, and clearances against KiCad
  libraries + datasheets before ordering boards.**

## Renders

| Raytraced 3D (KiCad) | 2D layout |
|---|---|
| ![top](https://www.kimi.com/apiv2-files/sign-obj/kimi-fs%2Ffiles%2Fblob%2Fe447e3be8870825bd9360b2faf80294eabfc63a85d3469c54beade14ea6915ca?filename=render3d_top.png&sig=7H0E7j9Hn66GJ7PAaqvp2T5XtopoTnaw0POVgIjmcMw=&t=o) | ![top](https://www.kimi.com/apiv2-files/sign-obj/kimi-fs%2Ffiles%2Fblob%2F4a3f37146991114d31e0e7d7301c1404902335d4c318d34e6f837ed87001703a?filename=render_top.png&sig=YfR5YqP6S8jgPKeqFnozCjWqNQv8KXiRiNNfZ6j_BEY=&t=o) |
| ![bottom](https://www.kimi.com/apiv2-files/sign-obj/kimi-fs%2Ffiles%2Fblob%2F0503637c3a3e45cb7459778846b78c1bff3dcd7011a83fe6adeea64aa91563c8?filename=render3d_bottom.png&sig=Kxg-iRaivtlBXaQo5xy5NmikO8erI6tXaVT4S7yIAAE=&t=o) | ![bottom](https://www.kimi.com/apiv2-files/sign-obj/kimi-fs%2Ffiles%2Fblob%2F6ebc4915986e48f085c2d90515e4a1d6fb0f5161a0abd8cc0c5b4cbab4652aab?filename=render_bottom.png&sig=KwGu3Yp1Iw0wf5bHdwkc7n-u9flTS-mEx46aXy22dJ8=&t=o) |

🎬 [360° turntable video](https://www.kimi.com/apiv2-files/sign-obj/kimi-fs%2Ffiles%2Fblob%2F3f08486e6f0ff1068fbd53782de2cc1f1788525d00661842cc8fa46822fbf88f?filename=turntable.gif&sig=Q4LmRTQu2VYfwpUxshEzN1dt57n0WfRyKvzQsstAcRE=&t=o) — 24 real KiCad raytraced frames stitched with ffmpeg (tools/turntable.sh).
