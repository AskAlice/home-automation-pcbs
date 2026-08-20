# WLED usermod for LEDHub C6

Single-header usermod (`usermod_ledhub.h`) that wires every LEDHub C6 peripheral
into WLED 0.15: ILI9341 status screen, EC11 rotary encoder, 5-way ADC button
ladder, LD2450 presence radar, SHT31 + BH1750 telemetry, INMP441 mic RMS.

Hardware: [`boards/ledhub-c6`](../../boards/ledhub-c6) — pin map is a fixed
contract (SPEC.md §4.5). Do not reassign pins without respinning the board.

## Install

1. Copy `usermod_ledhub.h` to `wled00/../usermods/ledhub/usermod_ledhub.h`
   (i.e. `usermods/ledhub/usermod_ledhub.h`) in your WLED source tree.
2. Register in `wled00/usermods_list.cpp`:

   ```cpp
   // top of file, with the other usermod includes
   #ifdef USERMOD_LEDHUB
     #include "../usermods/ledhub/usermod_ledhub.h"
   #endif

   // inside registerUsermods(), with the other registrations
   #ifdef USERMOD_LEDHUB
     registerUsermod(new LEDHubUsermod());
   #endif
   ```

3. Add to `platformio_override.ini`:

   ```ini
   [env:ledhub_c6]
   extends = env:esp32-c6
   build_flags =
     ${env:esp32-c6.build_flags}
     -D USERMOD_LEDHUB
     ; --- TFT_eSPI pin defines (match SPEC §4.5 exactly) ---
     -D USER_TFT_ESPI
     -D ILI9341_2_DRIVER
     -D TFT_WIDTH=240
     -D TFT_HEIGHT=320
     -D TFT_MOSI=7
     -D TFT_SCLK=6
     -D TFT_CS=5
     -D TFT_DC=4
     -D TFT_RST=1
     -D TFT_BL=2
     -D SPI_FREQUENCY=40000000
   lib_deps =
     ${env:esp32-c6.lib_deps}
     bodmer/TFT_eSPI @ ^2.5.43
     adafruit/Adafruit SHT31 Library @ ^2.2.2
     claws/BH1750 @ ^1.3.0
   ```

4. Set the LED output in the WLED UI: GPIO3, WS281x, 5 V — the board level-shifts
   through a 74AHCT125 with a 470 Ω series resistor, so no external shifter needed.

## Controls

| Input | Action |
|---|---|
| Encoder rotate | Brightness ±4 per detent |
| UP / DN buttons | Brightness ±10 |
| LF / RT buttons | Previous / next effect |
| OK button | Toggle power |
| LD2450 target present | Turn on (brightness `presenceBri`) |
| No target for `presenceOff_s` | Turn off |

Button ladder thresholds (12-bit ADC on GPIO0, 10k top resistor to 3V3):
UP=0R→≈0, DN=2k2→≈743, LF=4k7→≈1307, RT=10k→≈2048, OK=22k→≈2813.
Bands in `BTN_BANDS[]` tolerate 5 % resistors; recalibrate there if needed.

## Telemetry

When MQTT is configured in WLED, publishes every `telemetry_ms` (default 10 s)
to `ledhub/telemetry`:

```json
{"temp_c":22.35,"rh":44.2,"lux":153.0,"mic_rms":0.012,"presence":true}
```

The topic prefix and all thresholds are editable from the WLED usermod settings
page (`LEDHub` section) and persisted via `addToConfig()/readFromConfig()`.

## Notes / limitations

- Full sound-reactive effects require the **WLED-SR** fork; this usermod only
  exposes raw mic RMS on MQTT (INMP441 on I2S0, 16 kHz / 32-bit mono).
- The LD2450 parser only extracts "any target" presence (PIR-usermod semantics);
  multi-target coordinates are ignored.
- ESPHome alternative: `boards/ledhub-c6/esphome/ledhub-c6.yaml` implements the
  same peripherals without WLED.
