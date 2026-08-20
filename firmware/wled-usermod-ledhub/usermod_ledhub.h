#pragma once
/*
 * usermod_ledhub.h — WLED usermod for the LEDHub C6 all-in-one LED controller
 * Board: boards/ledhub-c6 (see README.md and SPEC.md §4.5 for the FIXED pin map)
 *
 * Target: WLED 0.15.x usermod API, ESP32-C6 (Wi-Fi 6 + 802.15.4).
 *
 * Features
 *  a) ILI9341 2.8" status screen (TFT_eSPI): effect name, palette, brightness
 *     bar, IP address, Wi-Fi RSSI, ~4 Hz refresh, backlight dims after 60 s idle.
 *  b) EC11 rotary encoder -> master brightness (state-machine quadrature decoder).
 *  c) 5-way nav buttons on a resistor ladder (single ADC pin):
 *       UP/DN = brightness +/-10, LF/RT = effect prev/next, OK = toggle power.
 *  d) LD2450 mmWave presence radar on Serial1 -> auto on/off like the PIR usermod.
 *  e) SHT31 (0x44) + BH1750 (0x23) on Wire -> MQTT topic ledhub/telemetry.
 *  f) INMP441 I2S mic: raw RMS level published on MQTT (full sound-reactive
 *     effects require the WLED-SR fork; wiring documented in README).
 *
 * Registration (in wled00/usermods_list.cpp):
 *   #ifdef USERMOD_LEDHUB
 *     #include "../usermods/ledhub/usermod_ledhub.h"
 *   #endif
 *   ...
 *   #ifdef USERMOD_LEDHUB
 *     registerUsermod(new LEDHubUsermod());
 *   #endif
 */

#ifdef USERMOD_LEDHUB

#include "wled.h"
#include <Wire.h>
#include <TFT_eSPI.h>          // configured via platformio_override.ini build_flags
#include <Adafruit_SHT31.h>    // "Adafruit SHT31 Library"
#include <BH1750.h>            // "BH1750" by Christopher Laws
#include <driver/i2s.h>

// ---------------------------------------------------------------- pin map (SPEC §4.5, FIXED)
#define PIN_TFT_SCK   6
#define PIN_TFT_MOSI  7
#define PIN_TFT_CS    5
#define PIN_TFT_DC    4
#define PIN_TFT_RST   1
#define PIN_TFT_BL    2
#define PIN_ENC_A     15
#define PIN_ENC_B     16
#define PIN_BTN_ADC   0    // ADC1_CH0, resistor ladder
#define PIN_I2S_SCK   17
#define PIN_I2S_WS    18
#define PIN_I2S_SD    19
#define PIN_I2C_SDA   20
#define PIN_I2C_SCL   21
#define PIN_RAD_RX    22   // MCU_RX <- radar TX
#define PIN_RAD_TX    23   // MCU_TX -> radar RX
// WS2812 data is GPIO3 -> 74AHCT125 -> strip (handled by WLED bus config, not this usermod)

// ADC button ladder thresholds (3.3 V, 10k top resistor; 12-bit ADC 0..4095).
// UP=0R -> 0 ; DN=2k2 -> ~743 ; LF=4k7 -> ~1307 ; RT=10k -> ~2048 ; OK=22k -> ~2813
// Band half-width chosen generously for 5% resistors.
struct BtnBand { uint16_t lo, hi; uint8_t id; };
enum : uint8_t { BTN_NONE=0, BTN_UP, BTN_DN, BTN_LF, BTN_RT, BTN_OK };
static const BtnBand BTN_BANDS[] = {
  {    0,  300, BTN_UP },
  {  450, 1050, BTN_DN },
  { 1100, 1550, BTN_LF },
  { 1750, 2350, BTN_RT },
  { 2550, 3100, BTN_OK },
};

class LEDHubUsermod : public Usermod {
public:
  // ---------------------------------------------------------- setup()
  void setup() override {
    // TFT
    pinMode(PIN_TFT_BL, OUTPUT);
    digitalWrite(PIN_TFT_BL, LOW);
    tft.init();
    tft.setRotation(1);          // 320x240 landscape
    tft.fillScreen(TFT_BLACK);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);

    // encoder (pins have no internal pull-ups routed on the ladder — board has 10k pull-ups)
    pinMode(PIN_ENC_A, INPUT_PULLUP);
    pinMode(PIN_ENC_B, INPUT_PULLUP);
    encState = (digitalRead(PIN_ENC_A) << 1) | digitalRead(PIN_ENC_B);

    // buttons
    analogSetPinAttenuation(PIN_BTN_ADC, ADC_11db);

    // I2C sensors
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    haveSht = sht.begin(0x44, &Wire);
    haveBh  = bh.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, 0x23, &Wire);

    // LD2450 radar @ 256000 baud
    Serial1.begin(256000, SERIAL_8N1, PIN_RAD_RX, PIN_RAD_TX);

    // INMP441 I2S mic (RMS telemetry only; WLED-SR needed for reactive FX)
    i2s_config_t cfg = {};
    cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
    cfg.sample_rate = 16000;
    cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;
    cfg.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;
    cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
    cfg.dma_buf_count = 4;
    cfg.dma_buf_len = 256;
    i2s_driver_install(I2S_NUM_0, &cfg, 0, nullptr);
    i2s_pin_config_t pins = {};
    pins.bck_io_num = PIN_I2S_SCK;
    pins.ws_io_num = PIN_I2S_WS;
    pins.data_in_num = PIN_I2S_SD;
    pins.data_out_num = I2S_PIN_NO_CHANGE;
    i2s_set_pin(I2S_NUM_0, &pins);

    lastActivity = millis();
    initDone = true;
  }

  // ---------------------------------------------------------- connected()
  void connected() override {
    ipKnown = true;
    needRedraw = true;
  }

  // ---------------------------------------------------------- loop()
  void loop() override {
    if (!initDone || strip.isUpdating()) return;
    uint32_t now = millis();

    handleEncoder();
    handleButtons();
    handleRadar();

    if (now - lastScreen >= 250) {          // ~4 Hz status refresh
      lastScreen = now;
      drawStatus();
    }
    if (now - lastTelemetry >= teleInterval) {
      lastTelemetry = now;
      publishTelemetry();
    }

    // backlight idle dim
    bool idle = (now - lastActivity > (uint32_t)displayTimeout * 1000UL);
    digitalWrite(PIN_TFT_BL, idle ? LOW : HIGH);
  }

  // ---------------------------------------------------- config (WLED UI)
  void addToConfig(JsonObject &root) override {
    JsonObject top = root.createNestedObject(F("LEDHub"));
    top[F("displayTimeout_s")] = displayTimeout;
    top[F("telemetry_ms")]     = teleInterval;
    top[F("mqtt_topic")]       = mqttTopic;
    top[F("presenceOff_s")]    = presenceOffDelay;
    top[F("presence_enable")]  = presenceEnabled;
  }

  bool readFromConfig(JsonObject &root) override {
    JsonObject top = root[F("LEDHub")];
    if (top.isNull()) return false;
    displayTimeout  = top[F("displayTimeout_s")] | displayTimeout;
    teleInterval    = top[F("telemetry_ms")]     | teleInterval;
    presenceOffDelay= top[F("presenceOff_s")]    | presenceOffDelay;
    presenceEnabled = top[F("presence_enable")]  | presenceEnabled;
    const char *t = top[F("mqtt_topic")];
    if (t) strlcpy(mqttTopic, t, sizeof(mqttTopic));
    return true;
  }

  uint16_t getId() override { return USERMOD_ID_UNSPECIFIED; }

private:
  // ------------------------------------------------------------ encoder
  void handleEncoder() {
    static const int8_t QEM[16] = {0,-1,1,0, 1,0,0,-1, -1,0,0,1, 0,1,-1,0};
    uint8_t s = (digitalRead(PIN_ENC_A) << 1) | digitalRead(PIN_ENC_B);
    int8_t d = QEM[(encState << 2) | s];
    encState = s;
    encAcc += d;
    if (encAcc >= 4)  { bumpBrightness(+4); encAcc = 0; }
    if (encAcc <= -4) { bumpBrightness(-4); encAcc = 0; }
  }

  void bumpBrightness(int delta) {
    int b = (int)bri + delta;
    bri = (uint8_t)constrain(b, 1, 255);
    stateUpdated(CALL_MODE_DIRECT_CHANGE);
    lastActivity = millis();
    needRedraw = true;
  }

  // ------------------------------------------------------------ buttons
  void handleButtons() {
    uint16_t v = analogRead(PIN_BTN_ADC);
    uint8_t b = BTN_NONE;
    for (auto &band : BTN_BANDS)
      if (v >= band.lo && v <= band.hi) { b = band.id; break; }
    if (b != BTN_NONE) lastActivity = millis();
    if (b != lastBtn) { lastBtn = b; btnSince = millis(); return; }   // debounce edge
    if (b == BTN_NONE || millis() - btnSince < 40 || btnFired) return;
    btnFired = true;
    switch (b) {
      case BTN_UP: bumpBrightness(+10); break;
      case BTN_DN: bumpBrightness(-10); break;
      case BTN_LF: applyEffect((effectCurrent + 1) % strip.getModeCount()); break;
      case BTN_RT: applyEffect(effectCurrent == 0 ? strip.getModeCount() - 1 : effectCurrent - 1); break;
      case BTN_OK: togglePower(); break;
    }
  }
  void applyEffect(uint16_t fx) { effectCurrent = fx; stateUpdated(CALL_MODE_DIRECT_CHANGE); needRedraw = true; }
  void applyPaletteNext() { effectPalette = (effectPalette + 1) % GRADIENT_PALETTE_COUNT; stateUpdated(CALL_MODE_DIRECT_CHANGE); }

  // ------------------------------------------------------------ radar (LD2450, 256000 8N1)
  // LD2450 target-report frames: header AA FF 03 00 ... tail 55 CC. We only need
  // "any target present" — same behaviour class as the WLED PIR usermod.
  void handleRadar() {
    static uint8_t buf[64]; static uint8_t idx = 0;
    while (Serial1.available()) {
      uint8_t c = Serial1.read();
      buf[idx++] = c;
      if (idx >= 2 && buf[idx-2] == 0x55 && c == 0xCC) {           // frame tail
        bool target = false;
        for (uint8_t i = 0; i + 1 < idx; i++)                      // crude: any non-zero payload
          if (buf[i] && i > 3) { target = true; break; }
        onPresence(target);
        idx = 0;
      }
      if (idx >= sizeof(buf)) idx = 0;
    }
  }

  void onPresence(bool present) {
    if (!presenceEnabled) return;
    uint32_t now = millis();
    if (present) {
      lastPresence = now;
      if (!powerWasOn && bri == 0) { bri = presenceBri; stateUpdated(CALL_MODE_DIRECT_CHANGE); }
      powerWasOn = true;
    } else if (powerWasOn && now - lastPresence > (uint32_t)presenceOffDelay * 1000UL) {
      bri = 0;
      stateUpdated(CALL_MODE_DIRECT_CHANGE);
      powerWasOn = false;
    }
  }

  // ------------------------------------------------------------ screen
  void drawStatus() {
    static uint32_t lastDraw = 0;
    if (!needRedraw && millis() - lastDraw < 1000) { /* refresh RSSI once a second anyway */ }
    lastDraw = millis();
    tft.fillScreen(TFT_BLACK);
    tft.setTextSize(2);
    tft.setCursor(4, 4);
    tft.printf("FX: %.18s", strip.getModeData(effectCurrent));
    tft.setCursor(4, 26);
    tft.printf("Pal: %u", effectPalette);

    // brightness bar
    int w = map(bri, 0, 255, 0, 300);
    tft.drawRect(4, 52, 304, 22, TFT_WHITE);
    tft.fillRect(6, 54, w, 18, bri ? TFT_GREEN : TFT_DARKGREY);
    tft.setCursor(4, 82);
    tft.printf("Bri: %u", bri);

    tft.setCursor(4, 110);
    if (ipKnown) tft.printf("IP: %s", WiFi.localIP().toString().c_str());
    else         tft.print("IP: (offline)");
    tft.setCursor(4, 134);
    tft.printf("RSSI: %d dBm", WiFi.RSSI());

    if (haveSht) {
      tft.setCursor(4, 162);
      tft.printf("%.1f C  %.0f %%rH", sht.readTemperature(), sht.readHumidity());
    }
    if (haveBh) {
      tft.setCursor(4, 186);
      tft.printf("%.0f lx", bh.readLightLevel());
    }
    needRedraw = false;
  }

  // ------------------------------------------------------------ telemetry
  void publishTelemetry() {
    if (!WLED_MQTT_CONNECTED) return;
    char payload[192];
    float t = haveSht ? sht.readTemperature() : NAN;
    float h = haveSht ? sht.readHumidity() : NAN;
    float lx = haveBh ? bh.readLightLevel() : NAN;
    snprintf(payload, sizeof(payload),
      "{\"temp_c\":%.2f,\"rh\":%.1f,\"lux\":%.1f,\"mic_rms\":%.1f,\"presence\":%s}",
      t, h, lx, micRms(), powerWasOn ? "true" : "false");
    char topic[64];
    snprintf(topic, sizeof(topic), "%s/%s", mqttTopic, "telemetry");  // default ledhub/telemetry
    mqtt->publish(topic, 0, false, payload);
  }

  float micRms() {
    int32_t raw[128]; size_t n = 0;
    if (i2s_read(I2S_NUM_0, raw, sizeof(raw), &n, 0) != ESP_OK || n == 0) return 0.0f;
    double acc = 0; size_t cnt = n / 4;
    for (size_t i = 0; i < cnt; i++) { double s = raw[i] / 2147483648.0; acc += s * s; }
    return cnt ? sqrt(acc / cnt) : 0.0f;
  }

  // ------------------------------------------------------------ state
  TFT_eSPI tft = TFT_eSPI();
  Adafruit_SHT31 sht;
  BH1750 bh;
  bool initDone = false, haveSht = false, haveBh = false, ipKnown = false, needRedraw = true;
  uint8_t encState = 0; int8_t encAcc = 0;
  uint8_t lastBtn = BTN_NONE; uint32_t btnSince = 0; bool btnFired = false;
  uint32_t lastActivity = 0, lastScreen = 0, lastTelemetry = 0, lastPresence = 0;
  bool powerWasOn = false;

  // config-backed
  uint16_t displayTimeout = 60;        // s, backlight idle dim
  uint32_t teleInterval = 10000;       // ms
  uint16_t presenceOffDelay = 60;      // s without target -> off
  bool presenceEnabled = true;
  uint8_t presenceBri = 128;
  char mqttTopic[24] = "ledhub";
};

#endif // USERMOD_LEDHUB
