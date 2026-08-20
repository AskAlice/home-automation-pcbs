# RelayMini C3 — inline mains switch + energy metering

> ⚠⚠ **MAINS SAFETY WARNING** ⚠⚠
> This board switches **mains voltage (110–240 VAC)**. Assembly, installation
> and use involve **lethal voltages**. Build it only if you are qualified to
> work with mains. Enclose the finished device in an insulated, strain-relieved
> enclosure. **NEVER connect USB or a programmer while mains is applied** —
> the entire primary side (including the BL0942 metering domain) is at mains
> potential. The programming header J3 is on the isolated SELV side only.
> Fuse F1 (10 A, 5×20 mm) is mandatory, not optional.

ESP32-C3 inline switch for ESPHome: HLK-PM01 AC/DC PSU, HF32F-G 10 A relay,
BL0942 energy metering (voltage / current / power / energy / frequency) with
PC817 opto-isolated UART.

## Features
- 10 A / 250 VAC relay switching (HF32F-G/005-HS)
- BL0942 metering, opto-isolated from the MCU domain
- On-board AC/DC (HLK-PM01, 5 V) + AP2112 3.3 V LDO
- User button (toggle) + status LED
- ESPHome `bl0942` component — see `esphome/relaymini-c3.yaml`

## Isolation design
- **≥6 mm creepage** between the live domain (AC_L/AC_N, HLK-PM01 primary,
  BL0942, opto live side) and the SELV domain (ESP32-C3, J3, button, LED).
- **Milled isolation slot** (Edge.Cuts) separating the domains, with a copper
  keepout beneath the PC817 optocouplers straddling the barrier.
- Live area is marked **"DANGER / MAINS VOLTAGE AREA"** on Dwgs.User.

## BOM
See `bom_lcsc.csv` (all parts are real, in-stock LCSC numbers; fuse F1 =
clip C3130 + 10 A element C3122; shunt R3 = 1 mΩ 2512 1 %).

## Pinout
| Function | GPIO |
|---|---|
| Relay driver (Q1 → K1 coil) | GPIO6 |
| BL0942 UART RX / TX | GPIO4 / GPIO5 |
| User button (active low) | GPIO9 |
| Status LED (active low) | GPIO8 |
| Prog header J3 (SELV): TX0/RX0 | GPIO21 / GPIO20 |

## Flashing
1. **Mains disconnected.** Power the board via the SELV 3V3/GND pins of J3
   from an isolated USB-UART adapter, or pre-flash the module.
2. `esphome run esphome/relaymini-c3.yaml`
3. Calibrate BL0942 per ESPHome docs against a known load.

## Routing status
Power domains and all safety-critical copper are routed and pass the
geometric self-check (0 cross-net violations, DFM-001=0). 24 nets retain
partial ratsnest (pruned during creepage-respecting routing): EN, Q1B,
RELAY, U5_A and stub legs of +3V3/+5V/COIL/TX0/RX0/VSENSE/MTR_*. These are
short, low-speed nets — complete them in KiCad or with an autorouter before
fabrication.

## Analyzer notes
- KO-001 (U4/U5 inside keepout): **intentional** — copper-free creepage
  barrier under the optocouplers.
- PM-001 (U1/K1, U5/J3 courtyard overlaps): inflation-only; physical bodies
  verified clear.
- PM-002 (F1 overhang, R10–R15 0.4 mm from edge): acceptable for hand
  assembly; F1 fuse clips intentionally overhang.
- RT-001 unrouted nets: see Routing status.
- SS-001/DS-00x sourcing gates: LCSC numbers are assigned; datasheets are
  synced at repo level (`datasheets/`).

## Disclaimer
**Verify every footprint against its manufacturer datasheet before
fabrication.** This is a v0.1 reference design that has not been fabricated
or safety-certified. Mains devices may require certification (CE/UL) in your
jurisdiction.

## Renders

| Raytraced 3D (KiCad) | 2D layout |
|---|---|
| ![top](render3d_top.png) | ![top](render_top.png) |
| ![bottom](render3d_bottom.png) | ![bottom](render_bottom.png) |

🎬 [360° turntable video](turntable.mp4) — 24 real KiCad raytraced frames stitched with ffmpeg (tools/turntable.sh).
