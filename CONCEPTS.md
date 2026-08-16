# Brainstorm — home-automation board concepts

Long-list from the design brainstorm. ✅ = designed in this repo.

## Designed

- ✅ **SenseNode C6** — ESP32-C6 environmental multisensor (SHT31 temp/hum,
  BH1750 lux, BMP280 pressure, AM312 PIR). One SKU serves ESPHome (Wi-Fi)
  *and* Matter-over-Thread/Zigbee thanks to the C6's 802.15.4 radio.
- ✅ **PresencePro C3** — HLK-LD2410(B) mmWave presence sensor + BH1750 lux
  (gate automations on ambient light) + ESP32-C3. Native ESPHome `ld2410`.
- ✅ **LEDQuad C3** — 4-channel AO3400 low-side PWM driver, 12–24 V in,
  AP63205 buck to 5 V, ESP32-C3. ESPHome `light.rgbw` / WLED friendly.
- ✅ **RelayMini C3** — inline mains switch: HLK-PM01 PSU, HF32F relay 10 A,
  BL0942 energy metering with PC817 opto-isolated UART, isolation slot.
- ✅ **LEDHub C6** — all-in-one display LED controller: 2.8" ILI9341 TFT,
  EC11 rotary encoder, 5-way nav buttons on one ADC pin (resistor ladder),
  INMP441 I2S mic, SHT31 + BH1750, LD2450 presence radar, 74AHCT125-level-shifted
  WS2812 output. Ships with a WLED usermod.

## Wave 2 (designed)

- ✅ **ThreadNode H2** — ESP32-H2 battery contact sensor / smart button
  (CR2032), Matter-over-Thread / Zigbee only, deep-sleep first design.
- ✅ **AirQuality S3** — ESP32-S3 + SCD40 CO₂ + SGP40 VOC + SHT40 + display header.
- ✅ **BlindDriver C6** — TMC2209 stepper roller-blind controller, ESPHome `cover`.
- ✅ **IRBlaster C3** — IR TX/RX climate-bridge for ESPHome `climate_ir`.
- ✅ **GardenProbe C6** — capacitive soil moisture + temp, deep-sleep Thread node,
  AAA or LiPo + LDO.
- ✅ **ThreadRCP H2** — USB OpenThread RCP / border-router dongle (ESP32-H2-MINI).

## Backlog (not designed yet)

- **MainsDimmer** — trailing-edge dimmer (hard; needs serious safety review).
