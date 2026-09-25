# Rolling Hardware Catalog — home-automation-pcbs

Last checked: 2026-09-25 12:00 UTC

This file tracks current/recommended MCUs, modules, SBCs, radios, displays, connectors and power parts from the primary vendors we design around. It is updated each run with **additions/changes since the prior run** and implications for future PCB concepts.

## Recent changes this run

- Added **GaragePilot C6** concept: ESP32-C6-WROOM-1 remains the preferred module for a new Wi-Fi 6 + Thread-capable actuator board.
- Confirmed **ESP32-C6-WROOM-1** (v1.4 datasheet) is in active production with 4/8/16 MB flash options, 18.0 × 25.5 mm, 23 GPIOs, 3.0–3.6 V.
- Noted **ESP32-C3-WROOM-02** is still current (v1.7 datasheet) but the C6 supersedes it for any new Wi-Fi + Thread board; no new C3-only concepts planned.
- **Heltec HT-CT62** (ESP32-C3 + SX1262 LoRa) is available and interesting for a future sub-GHz sensor, but not selected because GaragePilot benefits more from native 802.15.4/Matter.
- **LILYGO T7-C6** (ESP32-C6-MINI-1, ~$6.80) validates C6 module pricing/availability but uses the smaller MINI-1 footprint; WROOM-1 is preferred for our 2-layer designs with easier hand-soldering and more GPIOs.
- **Raspberry Pi Pico 2 W** (RP2350, 802.11n + BT 5.2, ~$7) is a strong alternative MCU, but ESP32-C6 is retained for ESPHome/Matter ecosystem compatibility.
- **Orange Pi Zero 2W / Zero 3** (Allwinner H618, Wi-Fi 5 + BT 5.0) are Linux SBCs, overkill for a simple actuator; no impact on this run.
- Relays and terminals: commodity **HF32F/12V** and **KF301-5.0-2P/3P** screw terminals are stocked at LCSC/JLCPCB and remain the safe choice for low-voltage switching boards.

## MCU / module comparison

| Part | Vendor | Core / wireless | Flash | Package | Voltage | Notes | Datasheet / source |
|---|---|---|---|---|---|---|---|
| ESP32-C6-WROOM-1-N8 | Espressif | RISC-V 160 MHz, Wi-Fi 6, BLE 5.3, 802.15.4 (Thread/Zigbee) | 8 MB | 18.0 × 25.5 × 3.2 mm, 28 SMD pads + EP | 3.0–3.6 V | Recommended for new ESPHome + Matter-over-Thread nodes. | https://documentation.espressif.com/esp32-c6-wroom-1_wroom-1u_datasheet_en.html |
| ESP32-C3-WROOM-02-N4 | Espressif | RISC-V 160 MHz, Wi-Fi 4, BLE 5 | 4 MB | 18.0 × 20.0 × 3.2 mm | 3.0–3.6 V | Mature, cheap, but lacks 802.15.4. | https://documentation.espressif.com/esp32-c3-wroom-02_datasheet_en.html |
| HT-CT62 | Heltec | ESP32-C3FN4 + SX1262 LoRa | 4 MB | 17.78 × 17.78 × 2.8 mm castellated | 2.7–3.5 V | Good for future sub-GHz outdoor sensors; not for garage actuator. | https://heltec.org/project/ht-ct62/ |
| T7-C6 | LILYGO | ESP32-C6-MINI-1 | 4 MB | 41 × 27 mm devboard | 5 V USB | Cheap C6 reference, confirms module availability. | https://lilygo.cc/en-us/products/t7-c6 |
| Raspberry Pi Pico 2 W | Raspberry Pi | RP2350 dual Cortex-M33 / Hazard3, 802.11n, BT 5.2 | 4 MB QSPI | 21 × 51 mm module | 1.8–5.5 V | Excellent alternative, but ESPHome support is weaker than ESP32. | https://www.raspberrypi.com/products/raspberry-pi-pico-2/ |
| Orange Pi Zero 2W/3 | Orange Pi | Allwinner H618 quad A53, Wi-Fi 5, BT 5.0 | TF/eMMC | 65 × 30 / 55 × 50 mm SBC | 5 V/3 A | Linux SBC, too big/power-hungry for this class of board. | http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_Zero_2W |

## Power / peripheral parts

| Category | Recommended part | Why |
|---|---|---|
| 3.3 V LDO | AP2112K-3.3TRG1 (SOT-23-5) | Used across existing boards; 600 mA, stable, cheap, LCSC C51115. |
| 5 V → 3.3 V when USB-powered | AP2112K direct from VBUS | GaragePilot is USB-C or 5 V terminal powered; no buck needed. |
| Low-voltage relay | HF32F-G-12-HS or HF3FA-12-1HS1T | 10 A contact, 12 V coil; 3.3 V coil variant also stocked. |
| Terminal block | KF301-5.0-2P / 3P | 5.0 mm pitch, 300 V/10 A, JLCPCB basic parts. |
| USB-C receptacle | TYPE-C-31-M-12 (16P mid-mount) | Used across existing boards; LCSC C165948. |
| Tactile switch | TS-1187A-B-A-B (6×6 SMD) | BOOT/RESET, LCSC C139797. |

## Implications for future concepts

- **GaragePilot C6** uses ESP32-C6-WROOM-1 because 802.15.4 enables Matter-over-Thread garage-door control later, while ESPHome Wi-Fi works today.
- Next likely concepts to fill remaining gaps: **WaterLeak C6** (capacitive leak detection), **ValveMaster C6** (24 VAC irrigation valve driver), or **SirenActuator C6** (alarm siren + strobe). All can reuse the C6 + AP2112 + terminal-block platform established here.
- Keep monitoring Espressif for ESP32-C61 or C5 modules; do **not** churn existing validated C6/C3 designs until a new module offers a concrete advantage and is generally available.

## Sources checked this run

- Espressif ESP32-C6-WROOM-1 datasheet v1.4 — https://documentation.espressif.com/esp32-c6-wroom-1_wroom-1u_datasheet_en.html (accessed 2026-09-25)
- Espressif ESP32-C3-WROOM-02 datasheet v1.7 — https://documentation.espressif.com/esp32-c3-wroom-02_datasheet_en.html (accessed 2026-09-25)
- Espressif part-number guide — https://developer.espressif.com/blog/2025/03/espressif-part-numbers-explained/ (accessed 2026-09-25)
- Heltec HT-CT62 product page / datasheet — https://heltec.org/project/ht-ct62/ (accessed 2026-09-25)
- LILYGO T7-C6 product page — https://lilygo.cc/en-us/products/t7-c6 (accessed 2026-09-25)
- Raspberry Pi Pico 2 / Pico 2 W product page — https://www.raspberrypi.com/products/raspberry-pi-pico-2/ (accessed 2026-09-25)
- Orange Pi Zero 2W wiki — http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_Zero_2W (accessed 2026-09-25)
- Orange Pi Zero 3 wiki — http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_Zero_3 (accessed 2026-09-25)
