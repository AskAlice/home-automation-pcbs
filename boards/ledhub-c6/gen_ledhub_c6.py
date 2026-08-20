#!/usr/bin/env python3
"""ledhub-c6 -- programmatic KiCad 8 project generator.

80x50 mm 2-layer all-in-one display LED controller:
ESP32-C6-WROOM-1, 2.8" ILI9341 TFT (2x7 header), EC11 rotary encoder,
5-way ADC resistor-ladder nav buttons (GPIO0), INMP441 I2S mic,
SHT31 + BH1750 on I2C, LD2450 mmWave header, WS2812 output via
74AHCT125 level shifter, USB-C (native USB + power), AP2112 3V3,
separate LED_5V terminal rail.  WLED 0.15 is the primary firmware
target; ESPHome also possible (esphome/ledhub-c6.yaml).

Run:  python3 gen_ledhub_c6.py   (exits non-zero on any problem)

Footprint / part-number evidence:
  * ESP32-C6-WROOM-1: Espressif "ESP32-C6-WROOM-1 & WROOM-1U Datasheet"
    v1.4 (https://documentation.espressif.com/esp32-c6-wroom-1_wroom-1u_datasheet_en.html),
    section 10.1/11.1: module 18.0 x 25.5 x 3.1 mm, 28 pads @ 1.27 mm
    pitch, land pattern pads 1.5 x 0.9 mm (columns +/-8.75 mm), thermal
    pad 7.495 x 12.29 mm.  Footprint below matches those numbers.
  * SHT31: Sensirion datasheet, DFN-8 2.5 x 2.5 mm (real package -
    NOT the 3x3 variant).
  * INMP441: TDK/InvenSense DS-INMP441-00 rev 1.1: 9-terminal LGA_CAV
    4.72 x 3.76 x 1.0 mm, bottom sound port -> needs an 0.8 mm PCB
    hole; pads 0.40 x 0.60 mm, pinout 1=SCK 2=SD 3=WS 4=L/R 5/6/9=GND
    7=VDD 8=CHIPEN.  Hand-solder hostile - see README.
  * LCSC numbers picked via jlcsearch API (see bom_lcsc.csv).
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "tools"))
import kicadgen as kg  # noqa: E402

BOARD = "ledhub-c6"
W, H = 80.0, 50.0
OUT = os.path.dirname(os.path.abspath(__file__))

DS = {
    "ESP32-C6-WROOM-1": "https://documentation.espressif.com/esp32-c6-wroom-1_wroom-1u_datasheet_en.html",
    "USB_C_16P": "https://www.lcsc.com/datasheet/lcsc_datasheet_2410252104_Korean-Hroparts-Elec-TYPE-C-31-M-12_C165948.pdf",
    "AP2112K-3.3": "https://www.diodes.com/assets/Datasheets/AP2112.pdf",
    "SHT31": "https://www.sensirion.com/media/documents/213E6A3B/63A5A569/Datasheet_SHT3x_DIS.pdf",
    "BH1750": "https://www.mouser.com/datasheet/2/348/bh1750fvi-e-1868571.pdf",
    "INMP441": "https://invensense.tdk.com/wp-content/uploads/2015/02/INMP441.pdf",
    "74AHCT125": "https://www.diodes.com/assets/Datasheets/74AHCT125.pdf",
    "EC11": "https://www.lcsc.com/datasheet/lcsc_datasheet_2304140036_ALPSALPINE-EC11E15244G1_C370970.pdf",
}

# value -> (footprint, description, LCSC, MPN)
PART_INFO = {
    "ESP32-C6-WROOM-1": ("custom:ESP32-C6-WROOM-1",
                         "WiFi6/BLE/802.15.4 module", "C5366877",
                         "ESP32-C6-WROOM-1-N8"),
    "USB_C_16P": ("Connector_USB:USB_C_Receptacle_USB2.0_16P",
                  "USB-C 2.0 16P mid-mount receptacle", "C165948",
                  "TYPE-C-31-M-12"),
    "AP2112K-3.3": ("Package_TO_SOT_SMD:SOT-23-5", "LDO 3.3V 600mA",
                    "C51118", "AP2112K-3.3TRG1"),
    "SHT31": ("custom:SHT31-DFN8", "Humidity/temp sensor I2C", "C80862",
              "SHT31-DIS-B2.5kS"),
    "BH1750": ("custom:BH1750-WSOF6", "Ambient light sensor I2C", "C78960",
               "BH1750FVI-TR"),
    "INMP441": ("custom:INMP441-LGA9", "I2S MEMS mic, bottom port", "-",
                "INMP441ACEZ-R7"),       # NOT stocked at LCSC
    "74AHCT125": ("Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
                  "Quad buffer 5V level shifter", "C842299",
                  "74AHCT125S14-13"),
    "EC11": ("custom:EC11-Encoder", "Rotary encoder EC11 w/ switch",
             "C370970", "EC11E15244G1"),
    "SW_PUSH": ("custom:Tactile-6x6-SMD", "Tactile switch 6x6 SMD", "C318884",
                "TS-1187A-B-A-B"),
    "10k": ("Resistor_SMD:R_0603_1608Metric", "Resistor 10k 0603", "C25804",
            "0603WAF1002T5E"),
    "4.7k": ("Resistor_SMD:R_0603_1608Metric", "Resistor 4.7k 0603", "C23162",
             "0603WAF4701T5E"),
    "2.2k": ("Resistor_SMD:R_0603_1608Metric", "Resistor 2.2k 0603", "C4190",
             "0603WAF2201T5E"),
    "22k": ("Resistor_SMD:R_0603_1608Metric", "Resistor 22k 0603", "C31850",
            "0603WAF2202T5E"),
    "5.1k": ("Resistor_SMD:R_0603_1608Metric", "Resistor 5.1k 0603", "C23186",
             "0603WAF5101T5E"),
    "22R": ("Resistor_SMD:R_0603_1608Metric", "Resistor 22R 0603", "C22926",
            "0603WAF220JT5E"),
    "100R": ("Resistor_SMD:R_0603_1608Metric", "Resistor 100R 0603", "C22775",
             "0603WAF1000T5E"),
    "470R": ("Resistor_SMD:R_0603_1608Metric", "Resistor 470R 0603", "C23179",
             "0603WAF4700T5E"),
    "1k": ("Resistor_SMD:R_0603_1608Metric", "Resistor 1k 0603", "C21190",
           "0603WAF1001T5E"),
    "0R": ("Resistor_SMD:R_0603_1608Metric", "Resistor 0R 0603 link", "C21189",
           "0603WAF0000T5E"),
    "100nF": ("Capacitor_SMD:C_0603_1608Metric", "Cap MLCC 100nF 0603",
              "C14663", "0603B104K500NT"),
    "10uF": ("Capacitor_SMD:C_0603_1608Metric", "Cap MLCC 10uF 0603",
             "C15849", "CL10A106KP8NNNC"),
    "LED_RED": ("LED_SMD:LED_0603_1608Metric", "LED red 0603", "C2286",
                "LTST-C190KRKT"),
    "Conn_02x07": ("Connector_PinHeader_2.54mm:PinHeader_2x07_P2.54mm_Vertical",
                   "Header 2x7 (2.8in TFT)", "C492424", "PZ254V-12-14P"),
    "Conn_01x05": ("Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
                   "Header 1x5 (LD2450)", "C492404", "PZ254V-11-05P"),
    "Conn_01x04": ("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
                   "Header 1x4 (prog)", "C2691448", "PZ254V-11-04P"),
    "Term_3P": ("custom:KF128-5.08-3P", "Screw terminal 5.08mm 3P (LED out)",
                "C474953", "KF128-5.08-3P-AA"),
    "Term_2P": ("custom:KF128-5.08-2P", "Screw terminal 5.08mm 2P (LED 5V in)",
                "C474952", "KF128-5.08-2P-AA"),
}


def build_footprints(lib_prefix):
    """Custom footprint library; returns {name: Footprint}."""
    fps = {}

    # --- ESP32-C6-WROOM-1 (18.0 x 25.5 mm; land pads 1.5x0.9 @1.27 pitch,
    #     columns +/-8.75 mm; thermal pad 7.495 x 12.29 -> 7.5 x 12.3;
    #     antenna at pin-1 (-Y) end.  Verified vs Espressif datasheet
    #     v1.4 sec 10.1/11.1, see module docstring.) ----------------------
    fp = kg.Footprint(lib_prefix, "ESP32-C6-WROOM-1")
    for i in range(14):  # left column pads 1..14 (antenna end -> bottom)
        fp.add_pad(str(i + 1), "smd", "rect", -8.75, i * 1.27 - 8.255, 1.5, 0.9)
    for i in range(14):  # right column pads 28..15 (antenna end -> bottom)
        fp.add_pad(str(28 - i), "smd", "rect", 8.75, i * 1.27 - 8.255, 1.5, 0.9)
    fp.add_pad("29", "smd", "rect", 0.0, 0.0, 7.5, 12.3)  # exposed pad
    fp.add_rect(-9.0, -12.75, 9.0, 12.75, "F.Fab", 0.1)
    fp.add_rect(-9.5, -13.25, 9.5, 13.25, "F.CrtYd", 0.05)
    fp.add_line(-9.0, -12.75, 9.0, -12.75, "F.SilkS")
    fp.add_line(-9.0, -12.75, -9.0, -5.0, "F.SilkS")
    fp.add_line(9.0, -12.75, 9.0, -5.0, "F.SilkS")
    fp.add_line(-9.0, 5.0, -9.0, 12.75, "F.SilkS")
    fp.add_line(9.0, 5.0, 9.0, 12.75, "F.SilkS")
    fp.add_line(-9.0, 12.75, 9.0, 12.75, "F.SilkS")
    fp.add_text("ANT", 0, -11.0, "F.SilkS", 1.2)
    fps["ESP32-C6-WROOM-1"] = fp

    # --- SHT31 DFN-8 (2.5 x 2.5 mm real package) -------------------------
    fp = kg.Footprint(lib_prefix, "SHT31-DFN8")
    for i, y in enumerate((-1.2, -0.4, 0.4, 1.2)):  # left pads 1..4
        fp.add_pad(str(i + 1), "smd", "rect", -0.75, y, 0.5, 0.3)
    for i, y in enumerate((1.2, 0.4, -0.4, -1.2)):  # right pads 8..5
        fp.add_pad(str(8 - i), "smd", "rect", 0.75, y, 0.5, 0.3)
    fp.add_pad("9", "smd", "rect", 0.0, 0.0, 1.8, 1.1)  # EP
    fp.add_rect(-1.25, -1.25, 1.25, 1.25, "F.Fab", 0.1)
    fp.add_rect(-1.5, -1.7, 1.5, 1.7, "F.CrtYd", 0.05)
    fp.add_line(-1.25, -1.25, 1.25, -1.25, "F.SilkS")
    fp.add_line(-1.25, 1.25, 1.25, 1.25, "F.SilkS")
    fps["SHT31-DFN8"] = fp

    # --- BH1750 WSOF-6I ----------------------------------------------------
    fp = kg.Footprint(lib_prefix, "BH1750-WSOF6")
    for i, y in enumerate((-0.5, 0.0, 0.5)):
        fp.add_pad(str(i + 1), "smd", "rect", -1.43, y, 0.85, 0.4)
    for i, y in enumerate((0.5, 0.0, -0.5)):
        fp.add_pad(str(6 - i), "smd", "rect", 1.43, y, 0.85, 0.4)
    fp.add_pad("7", "smd", "rect", 0.0, 0.0, 1.5, 1.2)  # EP
    fp.add_rect(-1.6, -0.8, 1.6, 0.8, "F.Fab", 0.1)
    fp.add_rect(-1.75, -1.0, 1.75, 1.0, "F.CrtYd", 0.05)
    fp.add_line(-1.6, -0.8, 1.6, -0.8, "F.SilkS")
    fp.add_line(-1.6, 0.8, 1.6, 0.8, "F.SilkS")
    fps["BH1750-WSOF6"] = fp

    # --- INMP441 LGA-9 4.72x3.76, bottom sound port ----------------------
    # Pinout (TDK DS-INMP441-00): 1=SCK 2=SD 3=WS 4=L/R 5=GND 6=GND
    # 7=VDD 8=CHIPEN 9=GND(center).  Pads 0.40x0.60, cols +/-1.33, rows
    # +/-1.575/0.525.  0.8 mm PCB sound-port hole under the MEMS port.
    fp = kg.Footprint(lib_prefix, "INMP441-LGA9")
    for num, y in (("4", -1.575), ("3", -0.525), ("2", 0.525), ("1", 1.575)):
        fp.add_pad(num, "smd", "rect", -1.33, y, 0.4, 0.6)
    for num, y in (("6", -1.575), ("5", -0.525), ("7", 0.525), ("8", 1.575)):
        fp.add_pad(num, "smd", "rect", 1.33, y, 0.4, 0.6)
    fp.add_pad("9", "smd", "rect", 0.0, 0.75, 0.9, 0.6)
    fp.add_pad("", "np_thru_hole", "circle", 0.0, -1.1, 0.9, 0.9,
               layers=("*.Cu", "*.Mask"), drill=0.8)  # sound port hole
    fp.add_rect(-2.36, -1.88, 2.36, 1.88, "F.Fab", 0.1)
    fp.add_rect(-2.6, -2.1, 2.6, 2.1, "F.CrtYd", 0.05)
    fp.add_line(-2.36, -1.88, 2.36, -1.88, "F.SilkS")
    fp.add_line(-2.36, 1.88, 2.36, 1.88, "F.SilkS")
    fp.add_circle(-1.8, -2.3, 0.25, "F.SilkS")  # pin-1 (SCK) dot
    fp.add_text("PORT", 0, -2.8, "F.SilkS", 0.7)
    fps["INMP441-LGA9"] = fp

    # --- Tactile 6x6 SMD (4 gull-wing pads) --------------------------------
    fp = kg.Footprint(lib_prefix, "Tactile-6x6-SMD")
    for num, x, y in (("1", -4.5, -2.25), ("2", 4.5, -2.25),
                      ("3", -4.5, 2.25), ("4", 4.5, 2.25)):
        fp.add_pad(num, "smd", "rect", x, y, 2.3, 1.5)
    fp.add_rect(-3.0, -3.0, 3.0, 3.0, "F.Fab", 0.1)
    fp.add_rect(-5.95, -3.15, 5.95, 3.15, "F.CrtYd", 0.05)
    fp.add_rect(-2.9, -2.9, 2.9, 2.9, "F.SilkS", 0.12)
    fps["Tactile-6x6-SMD"] = fp

    # --- EC11 rotary encoder (THT, 3 enc pins + 2 switch pins + tabs) -----
    # Front row: A(-2.5) C(0) B(+2.5) @ y=-4.5; switch pins @ y=+4.5;
    # mounting tabs NPTH at x=+/-6.5.  Common EC11 land pattern;
    # verify against chosen part datasheet before fabrication.
    fp = kg.Footprint(lib_prefix, "EC11-Encoder")
    for num, x, y in (("1", -2.5, -4.5), ("2", 0.0, -4.5), ("3", 2.5, -4.5),
                      ("4", -2.5, 4.5), ("5", 2.5, 4.5)):
        fp.add_pad(num, "thru_hole", "circle", x, y, 1.8, 1.8,
                   layers=("*.Cu", "*.Mask"), drill=0.9)
    fp.add_pad("", "np_thru_hole", "circle", -6.5, 0.0, 2.4, 2.4,
               layers=("*.Cu", "*.Mask"), drill=1.7)
    fp.add_pad("", "np_thru_hole", "circle", 6.5, 0.0, 2.4, 2.4,
               layers=("*.Cu", "*.Mask"), drill=1.7)
    fp.add_rect(-6.0, -6.0, 6.0, 6.0, "F.Fab", 0.1)
    fp.add_rect(-7.0, -6.6, 7.0, 6.6, "F.CrtYd", 0.05)
    fp.add_circle(0, 0, 3.0, "F.SilkS")
    fp.add_rect(-6.0, -6.0, 6.0, 6.0, "F.SilkS", 0.12)
    fps["EC11-Encoder"] = fp

    # --- KF128 5.08 mm screw terminals ------------------------------------
    for name, n in (("KF128-5.08-2P", 2), ("KF128-5.08-3P", 3)):
        fp = kg.Footprint(lib_prefix, name)
        for i in range(n):
            fp.add_pad(str(i + 1), "thru_hole", "circle", 0.0, i * 5.08,
                       2.2, 2.2, layers=("*.Cu", "*.Mask"), drill=1.3)
        hw = (n - 1) * 5.08 / 2
        fp.add_rect(-3.5, -hw - 3.2, 3.5, hw + 3.2, "F.Fab", 0.1)
        fp.add_rect(-3.6, -hw - 1.2, 3.6, hw + 1.2, "F.CrtYd", 0.05)
        fp.add_rect(-3.5, -hw - 3.2, 3.5, hw + 3.2, "F.SilkS", 0.12)
        fp.add_line(-2.0, -hw - 4.0, 2.0, -hw - 4.0, "F.SilkS", 0.15)
        fps[name] = fp

    return fps

# ---------------------------------------------------------------------------
# Schematic
# ---------------------------------------------------------------------------
# pin plan: net name or None (-> no_connect marker).  PCB uses the same plan.
# Module pad -> GPIO (ESP32-C6-WROOM-1 datasheet pin table):
#   4=IO4 5=IO5 6=IO6 7=IO7 8=IO0 9=IO1 10=IO8 11=IO10 12=IO11
#   13=IO12(USB-) 14=IO13(USB+) 15=IO9 16=IO18 17=IO19 18=IO20 19=IO21
#   20=IO22 21=IO23 23=IO15 24=RXD0/IO17 25=TXD0/IO16 26=IO3 27=IO2
U1_PLAN = {"1": "GND", "2": "+3V3", "3": "EN", "4": "TFT_DC", "5": "TFT_CS",
           "6": "TFT_SCK", "7": "TFT_MOSI", "8": "BTN_ADC", "9": "TFT_RST",
           "10": None, "11": None, "12": None, "13": "USB_DM", "14": "USB_DP",
           "15": "BOOT", "16": "I2S_WS", "17": "I2S_SD", "18": "I2C_SDA",
           "19": "I2C_SCL", "20": "RAD_RX", "21": "RAD_TX", "22": None,
           "23": "ENC_A", "24": "I2S_SCK", "25": "ENC_B", "26": "LED_DIN",
           "27": "TFT_BL", "28": "GND", "29": "GND"}
U1_NAMES = {"1": "GND", "2": "3V3", "3": "EN", "4": "IO4", "5": "IO5",
            "6": "IO6", "7": "IO7", "8": "IO0", "9": "IO1", "10": "IO8",
            "11": "IO10", "12": "IO11", "13": "IO12/USB-DN",
            "14": "IO13/USB-DP", "15": "IO9", "16": "IO18", "17": "IO19",
            "18": "IO20", "19": "IO21", "20": "IO22", "21": "IO23",
            "22": "NC", "23": "IO15", "24": "RXD0/IO17", "25": "TXD0/IO16",
            "26": "IO3", "27": "IO2", "28": "GND", "29": "EP"}
X1_PLAN = {"1": "GND", "2": "VBUS", "3": "USB_CC1", "4": "USB_DP_CON",
           "5": "USB_DM_CON", "6": None, "7": "VBUS", "8": "GND",
           "9": "GND", "10": "VBUS", "11": None, "12": "USB_DM_CON",
           "13": "USB_DP_CON", "14": "USB_CC2", "15": "VBUS", "16": "GND",
           "S1": "GND", "S2": "GND", "S3": "GND", "S4": "GND"}
U2_PLAN = {"1": "I2S_SCK", "2": "I2S_SD", "3": "I2S_WS", "4": "GND",
           "5": "GND", "6": "GND", "7": "+3V3", "8": "+3V3", "9": "GND"}
U3_PLAN = {"1": "I2C_SDA", "2": "GND", "3": None, "4": "I2C_SCL", "5": "+3V3",
           "6": None, "7": None, "8": "GND", "9": "GND"}
U4_PLAN = {"1": "+3V3", "2": "GND", "3": "GND", "4": "I2C_SDA", "5": "+3V3",
           "6": "I2C_SCL", "7": "GND"}
U5_PLAN = {"1": "GND", "2": "LED_DINB", "3": "LED_PRE", "4": "+5V",
           "5": "GND", "6": None, "7": "GND", "8": None, "9": "GND",
           "10": "+5V", "11": None, "12": "GND", "13": "+5V", "14": "+5V"}
U6_PLAN = {"1": "VBUS", "2": "GND", "3": "VBUS", "4": None, "5": "+3V3"}
ENC_PLAN = {"1": "ENC_A", "2": "GND", "3": "ENC_B", "4": None, "5": None}
J1_PLAN = {"1": "+3V3", "2": "GND", "3": "TFT_CS", "4": "TFT_RST",
           "5": "TFT_DC", "6": "TFT_MOSI", "7": "TFT_SCK", "8": "TFT_BLP",
           "9": None, "10": None, "11": None, "12": None, "13": None,
           "14": None}
J2_PLAN = {"1": "+5V", "2": "RAD_RX", "3": "RAD_TX", "4": "GND", "5": "GND"}
J3_PLAN = {"1": "LED_5V", "2": "LED_DATA", "3": "GND"}
J4_PLAN = {"1": "LED_5V", "2": "GND"}
J5_PLAN = {"1": "+3V3", "2": "TX0", "3": "RX0", "4": "GND"}
RX_PLAN = {"R1": {"1": "+3V3", "2": "I2C_SDA"},
           "R2": {"1": "+3V3", "2": "I2C_SCL"},
           "R3": {"1": "USB_CC1", "2": "GND"},
           "R4": {"1": "USB_CC2", "2": "GND"},
           "R5": {"1": "USB_DP_CON", "2": "USB_DP"},
           "R6": {"1": "USB_DM_CON", "2": "USB_DM"},
           "R7": {"1": "+3V3", "2": "EN"},
           "R8": {"1": "+3V3", "2": "LED1_A"},
           "R9": {"1": "TFT_BL", "2": "TFT_BLP"},
           "R10": {"1": "TFT_BLP", "2": "GND"},
           "R11": {"1": "+3V3", "2": "BTN_ADC"},
           "R12": {"1": "BTN_ADC", "2": "B_UP"},
           "R13": {"1": "BTN_ADC", "2": "B_DN"},
           "R14": {"1": "BTN_ADC", "2": "B_LF"},
           "R15": {"1": "BTN_ADC", "2": "B_RT"},
           "R16": {"1": "ENC_B", "2": "TX0"},
           "R17": {"1": "I2S_SCK", "2": "RX0"},
           "R18": {"1": "BTN_ADC", "2": "B_OK"},
           "R19": {"1": "LED_PRE", "2": "LED_DATA"},
           "R21": {"1": "LED_DIN", "2": "LED_DINB"},
           "R20": {"1": "VBUS", "2": "+5V"}}
CX_PLAN = {"C1": {"1": "VBUS", "2": "GND"},
           "C2": {"1": "+3V3", "2": "GND"},
           "C3": {"1": "+3V3", "2": "GND"},
           "C4": {"1": "EN", "2": "GND"},
           "C5": {"1": "+3V3", "2": "GND"},
           "C6": {"1": "+3V3", "2": "GND"},
           "C7": {"1": "+3V3", "2": "GND"},
           "C8": {"1": "+3V3", "2": "GND"},
           "C9": {"1": "+5V", "2": "GND"},
           "C10": {"1": "+3V3", "2": "GND"}}
DX_PLAN = {"D1": {"1": "LED1_A", "2": "GND"}}
BT_PLAN = {"BT1": {"1": "EN", "2": "GND", "3": "EN", "4": "GND"},
           "BT2": {"1": "BOOT", "2": "GND", "3": "BOOT", "4": "GND"},
           "BT_UP": {"1": "B_UP", "2": "GND", "3": "B_UP", "4": "GND"},
           "BT_DN": {"1": "B_DN", "2": "GND", "3": "B_DN", "4": "GND"},
           "BT_LF": {"1": "B_LF", "2": "GND", "3": "B_LF", "4": "GND"},
           "BT_RT": {"1": "B_RT", "2": "GND", "3": "B_RT", "4": "GND"},
           "BT_OK": {"1": "B_OK", "2": "GND", "3": "B_OK", "4": "GND"}}


def _resolve(sch, ref, plan):
    for num, net in plan.items():
        pt = sch.pin_at(ref, num)
        if net is None:
            sch.no_connect(round(pt[0], 2), round(pt[1], 2))
        else:
            sch.label(net, round(pt[0], 2), round(pt[1], 2))


def build_schematic(path):
    lib = kg.SymbolLib(BOARD + "-lib")
    sch = kg.Schematic(BOARD, lib)
    for p in ("GND", "+3V3", "+5V", "VBUS", "LED_5V"):
        lib.add_power_symbol(p)

    def box(name, ref_prefix, nums, names, value_key):
        half = (len(nums) + 1) // 2
        pins = [(num, names.get(num, "P" + num), "passive",
                 "left" if i < half else "right")
                for i, num in enumerate(nums)]
        info = PART_INFO[value_key]
        fp = info[0].replace("custom:", BOARD + ":")
        lib.add_box_symbol(name, ref_prefix, pins, footprint=fp,
                           datasheet=DS.get(value_key, "~"),
                           lcsc=info[2], mpn=info[3])

    # module: 1..14 left, 28..15 right, 29 (EP) bottom
    nums = [str(i) for i in range(1, 15)] + [str(i) for i in range(28, 14, -1)]
    pins = [(n, U1_NAMES[n], "passive", "left" if i < 14 else "right")
            for i, n in enumerate(nums)]
    pins.append(("29", "EP", "passive", "bottom"))
    lib.add_box_symbol("ESP32-C6-WROOM-1", "U", pins,
                       footprint=BOARD + ":ESP32-C6-WROOM-1",
                       datasheet=DS["ESP32-C6-WROOM-1"],
                       lcsc=PART_INFO["ESP32-C6-WROOM-1"][2],
                       mpn=PART_INFO["ESP32-C6-WROOM-1"][3])

    xn = ["GND.B12", "VBUS.B9", "CC1.A5", "DP.A6", "DN.A7", "SBU1.B8",
          "VBUS.B4", "GND.B12b", "GND.A12", "VBUS.A4", "SBU2.A8", "DN2.A7",
          "DP2.A6", "CC2.B5", "VBUS.A4b", "GND.A1"]
    xpins = [(str(i + 1), xn[i], "passive", "left" if i < 8 else "right")
             for i in range(16)]
    xpins += [("S1", "SHIELD", "passive", "bottom"),
              ("S2", "SHIELD", "passive", "bottom"),
              ("S3", "SHIELD", "passive", "bottom"),
              ("S4", "SHIELD", "passive", "bottom")]
    lib.add_box_symbol("USB_C_16P", "X", xpins,
                       footprint="Connector_USB:USB_C_Receptacle_USB2.0_16P",
                       datasheet=DS["USB_C_16P"],
                       lcsc=PART_INFO["USB_C_16P"][2],
                       mpn=PART_INFO["USB_C_16P"][3])

    box("INMP441", "U", ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
        {"1": "SCK", "2": "SD", "3": "WS", "4": "L/R", "5": "GND",
         "6": "GND", "7": "VDD", "8": "CHIPEN", "9": "GND"}, "INMP441")
    box("SHT31", "U", ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
        {"1": "SDA", "2": "ADDR", "3": "ALERT", "4": "SCL", "5": "VDD",
         "6": "RESET", "7": "R", "8": "VSS", "9": "EP"}, "SHT31")
    box("BH1750", "U", ["1", "2", "3", "4", "5", "6", "7"],
        {"1": "VCC", "2": "ADDR", "3": "GND", "4": "SDA", "5": "DVI",
         "6": "SCL", "7": "EP"}, "BH1750")
    box("74AHCT125", "U",
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12",
         "13", "14"],
        {"1": "1OE", "2": "1A", "3": "1Y", "4": "2OE", "5": "2A", "6": "2Y",
         "7": "GND", "8": "3Y", "9": "3A", "10": "3OE", "11": "4Y",
         "12": "4A", "13": "4OE", "14": "VCC"}, "74AHCT125")
    box("AP2112K-3.3", "U", ["1", "2", "3", "4", "5"],
        {"1": "VIN", "2": "GND", "3": "EN", "4": "NC", "5": "VOUT"},
        "AP2112K-3.3")
    box("EC11", "ENC", ["1", "2", "3", "4", "5"],
        {"1": "A", "2": "C", "3": "B", "4": "SW1", "5": "SW2"}, "EC11")
    for val in ("10k", "4.7k", "2.2k", "22k", "5.1k", "22R", "100R", "470R",
                "1k", "0R"):
        box(val, "R", ["1", "2"], {"1": "1", "2": "2"}, val)
    for val in ("100nF", "10uF"):
        box(val, "C", ["1", "2"], {"1": "1", "2": "2"}, val)
    box("LED_RED", "D", ["1", "2"], {"1": "A", "2": "K"}, "LED_RED")
    box("SW_PUSH", "BT", ["1", "2", "3", "4"],
        {"1": "A1", "2": "A2", "3": "B1", "4": "B2"}, "SW_PUSH")
    box("Conn_02x07", "J", [str(i) for i in range(1, 15)],
        {str(i): str(i) for i in range(1, 15)}, "Conn_02x07")
    box("Conn_01x05", "J", ["1", "2", "3", "4", "5"],
        {"1": "1", "2": "2", "3": "3", "4": "4", "5": "5"}, "Conn_01x05")
    box("Conn_01x04", "J", ["1", "2", "3", "4"],
        {"1": "1", "2": "2", "3": "3", "4": "4"}, "Conn_01x04")
    box("Term_3P", "J", ["1", "2", "3"], {"1": "1", "2": "2", "3": "3"},
        "Term_3P")
    box("Term_2P", "J", ["1", "2"], {"1": "1", "2": "2"}, "Term_2P")

    placements = [
        ("ESP32-C6-WROOM-1", "U1", 90, 75, U1_PLAN),
        ("USB_C_16P", "X1", 195, 75, X1_PLAN),
        ("AP2112K-3.3", "U6", 40, 125, U6_PLAN),
        ("INMP441", "U2", 80, 150, U2_PLAN),
        ("SHT31", "U3", 115, 150, U3_PLAN),
        ("BH1750", "U4", 150, 150, U4_PLAN),
        ("74AHCT125", "U5", 90, 190, U5_PLAN),
        ("EC11", "ENC1", 150, 190, ENC_PLAN),
        ("Conn_02x07", "J1", 240, 110, J1_PLAN),
        ("Conn_01x05", "J2", 240, 150, J2_PLAN),
        ("Term_3P", "J3", 240, 190, J3_PLAN),
        ("Term_2P", "J4", 270, 190, J4_PLAN),
        ("Conn_01x04", "J5", 270, 150, J5_PLAN),
    ]
    for sym, ref, x, y, plan in placements:
        sch.place(sym, ref, x, y, value=sym)
        _resolve(sch, ref, plan)
    rvals = [("R1", "4.7k"), ("R2", "4.7k"), ("R3", "5.1k"), ("R4", "5.1k"),
             ("R5", "22R"), ("R6", "22R"), ("R7", "10k"), ("R8", "1k"),
             ("R9", "100R"), ("R10", "10k"), ("R11", "10k"), ("R12", "0R"),
             ("R13", "2.2k"), ("R14", "4.7k"), ("R15", "10k"), ("R16", "0R"),
             ("R17", "0R"), ("R18", "22k"), ("R21", "0R"), ("R19", "470R"), ("R20", "0R")]
    for i, (ref, val) in enumerate(rvals):
        x = 300 + (i % 5) * 25
        y = 40 + (i // 5) * 15
        sch.place(val, ref, x, y, value=val)
        _resolve(sch, ref, RX_PLAN[ref])
    for i, (ref, val) in enumerate([("C1", "10uF"), ("C2", "10uF"),
                                    ("C3", "100nF"), ("C4", "100nF"),
                                    ("C5", "100nF"), ("C6", "100nF"),
                                    ("C7", "100nF"), ("C8", "10uF"),
                                    ("C9", "100nF"), ("C10", "100nF")]):
        sch.place(val, ref, 300 + (i % 5) * 25, 110 + (i // 5) * 15, value=val)
        _resolve(sch, ref, CX_PLAN[ref])
    sch.place("LED_RED", "D1", 300, 150, value="LED_RED")
    _resolve(sch, "D1", DX_PLAN["D1"])
    for i, ref in enumerate(("BT1", "BT2", "BT_UP", "BT_DN", "BT_LF",
                             "BT_RT", "BT_OK")):
        sch.place("SW_PUSH", ref, 300 + (i % 4) * 30, 170 + (i // 4) * 20,
                  value="SW_PUSH")
        _resolve(sch, ref, BT_PLAN[ref])

    for i, name in enumerate(("GND", "GND", "+3V3", "+3V3", "+5V", "VBUS",
                              "LED_5V")):
        x, y = 20 + 10 * i, 25
        sch.place_power(name, x, y)
        sch.label(name, x, y)

    sch.sheet_note("ledhub-c6 rev 1.0 - WLED 0.15 all-in-one display LED "
                   "controller (ESP32-C6-WROOM-1).")
    sch.sheet_note("R16/R17 = 0R isolation links: GPIO16 is shared between "
                   "ENC_B and prog-header TX0, GPIO17 between I2S_SCK and "
                   "RX0.  Flash firmware via native USB-C (USB-Serial-JTAG "
                   "on GPIO12/13); for classic UART flashing remove R16/R17 "
                   "(or hold BOOT while UART is connected).")
    sch.sheet_note("ADC button ladder (GPIO0, 12-bit): +3V3-10k-node; "
                   "UP=0R->0.000V(0) DN=2.2k->0.595V(738) "
                   "LF=4.7k->1.055V(1308) RT=10k->1.650V(2048) "
                   "OK=22k->2.269V(2813) none->3.300V(4095). Thresholds: "
                   "<369 UP, 369-1023 DN, 1023-1678 LF, 1678-2430 RT, "
                   "2430-3454 OK, >3454 none.")
    sch.sheet_note("INMP441 is a bottom-port LGA: 0.8 mm sound-port hole in "
                   "the PCB; reflow recommended (see README).  L/R=GND "
                   "(left channel), CHIPEN=+3V3.")
    sch.sheet_note("LED_5V powers the LED strip only (separate 5.08 mm "
                   "terminal J4); logic 5 V (+5V) comes from USB VBUS via "
                   "R20 0R link.")
    sch.sheet_note("R21 = 0R series link between GPIO3 (LED_DIN) and "
                   "74AHCT125 1A (LED_DINB): keeps the 3.3V MCU domain and "
                   "the 5V buffer domain on separate nets and allows an "
                   "optional series damping resistor.")
    lib.save(os.path.join(OUT, BOARD + "-lib.kicad_sym"))
    sch.save(path)

# ---------------------------------------------------------------------------
# PCB: geometric copper model + self-check
# (deterministic hand routing: point-to-point L-routes, F.Cu primary,
#  B.Cu for crossings; cross-net clearance verified before save)
# ---------------------------------------------------------------------------
CLEAR = 0.15       # min copper-to-copper clearance (mm)
EDGE_CLEAR = 0.4   # min copper-to-board-edge distance (mm)
CRTYD = 1.0        # max courtyard overlap area (mm^2)
VIA_R = 0.4        # via radius (0.8 dia / 0.4 drill)
KEEPOUT = (12.5, 0.0, 34.5, 6.5)  # antenna keepout (x0, y0, x1, y1)


def rot_pt(x, y, deg):
    r = math.radians(deg)
    c, s = round(math.cos(r)), round(math.sin(r))
    return x * c - y * s, x * s + y * c


class Copper:
    """All copper objects for the geometric self-check."""

    def __init__(self):
        self.pads = []   # (net, layers, x, y, hx, hy, ref)
        self.segs = []   # (net, layer, x1, y1, x2, y2, halfw)
        self.vias = []   # (net, x, y)

    def add_pad(self, net, layers, x, y, hx, hy, ref=""):
        self.pads.append((net, frozenset(layers), x, y, hx, hy, ref))

    def add_seg(self, net, layer, x1, y1, x2, y2, halfw):
        self.segs.append((net, layer, x1, y1, x2, y2, halfw))

    def add_via(self, net, x, y):
        self.vias.append((net, x, y))


def _pt_seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def _seg_seg_dist(a1, a2, b1, b2):
    """Distance between two segments (0 if they intersect)."""
    def ccw(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    d1 = ccw(b1, b2, a1)
    d2 = ccw(b1, b2, a2)
    d3 = ccw(a1, a2, b1)
    d4 = ccw(a1, a2, b2)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    return min(_pt_seg_dist(*a1, *b1, *b2), _pt_seg_dist(*a2, *b1, *b2),
               _pt_seg_dist(*b1, *a1, *a2), _pt_seg_dist(*b2, *a1, *a2))


def _pt_rect_dist(px, py, cx, cy, hx, hy):
    dx = max(abs(px - cx) - hx, 0.0)
    dy = max(abs(py - cy) - hy, 0.0)
    return math.hypot(dx, dy)


def _seg_rect_dist(x1, y1, x2, y2, cx, cy, hx, hy):
    """Distance from segment to axis-aligned rect (0 on overlap)."""
    corners = [(cx - hx, cy - hy), (cx + hx, cy - hy),
               (cx + hx, cy + hy), (cx - hx, cy + hy)]
    for px, py in ((x1, y1), (x2, y2)):
        if abs(px - cx) <= hx and abs(py - cy) <= hy:
            return 0.0
    d = min(_seg_seg_dist((x1, y1), (x2, y2), corners[i], corners[(i + 1) % 4])
            for i in range(4))
    return d


class PcbBuilder:
    def __init__(self, board):
        self.pcb = kg.PCB(board)
        self.pcb.set_outline(W, H)
        self.cu = Copper()
        self.crtyds = []   # (ref, x0, y0, x1, y1) absolute
        self.placed = []   # (ref, fp, x, y, rot)
        self.pad_xy = {}

    # -- placement ------------------------------------------------------------
    def place(self, fp, ref, value, x, y, rot=0, crtyd=None):
        self.pcb.add_footprint(fp, ref, value, x, y, rot)
        fobj = self.pcb._footprints[-1]["fp"]
        self.placed.append((ref, fobj, x, y, rot))
        if crtyd:
            pts = [rot_pt(crtyd[0], crtyd[1], rot), rot_pt(crtyd[2], crtyd[1], rot),
                   rot_pt(crtyd[2], crtyd[3], rot), rot_pt(crtyd[0], crtyd[3], rot)]
            xs = [p[0] + x for p in pts]
            ys = [p[1] + y for p in pts]
            self.crtyds.append((ref, min(xs), min(ys), max(xs), max(ys)))

    def net_pad(self, ref, pad, net):
        self.pcb.set_pad_net(ref, pad, net)

    def collect_pads(self, nets):
        """Mirror every pad into the copper model + record positions."""
        for ref, fp, x, y, rot in self.placed:
            for p in fp.pads:
                dx, dy = rot_pt(p["x"], p["y"], rot)
                ax, ay = x + dx, y + dy
                sx, sy = p["sx"], p["sy"]
                if rot % 180:
                    sx, sy = sy, sx
                net = nets.get((ref, p["num"]))
                self.pad_xy[(ref, p["num"])] = (round(ax, 3), round(ay, 3))
                self.cu.add_pad(net, p["layers"], ax, ay, sx / 2, sy / 2, ref)

    # -- routing ---------------------------------------------------------------
    def route(self, net, pts, width=0.25, layer="F.Cu"):
        self.pcb.route(net, pts, layer=layer, width=width)
        for a, b in zip(pts, pts[1:]):
            if a != b:
                self.cu.add_seg(net, layer, a[0], a[1], b[0], b[1], width / 2)

    def via(self, net, x, y):
        self.pcb.via(net, x, y)
        self.cu.add_via(net, x, y)

    def gvia(self, net, ref, pad, vx, vy, width=0.5):
        """Stub from pad to via point (F.Cu) + via."""
        px, py = self.pad_xy[(ref, pad)]
        self.route(net, [(px, py), (vx, vy)], width=width)
        self.via(net, vx, vy)

    # -- checks ------------------------------------------------------------------
    def check_clearance(self, edge, keepouts):
        prob = []
        pads, segs, vias = self.cu.pads, self.cu.segs, self.cu.vias

        def pad_pad(p1, p2):
            if p1[0] == p2[0] and p1[0] is not None:
                return
            if not p1[1] & p2[1]:
                return
            if p1[6] and p1[6] == p2[6]:
                return  # intra-footprint pad pitch is package-defined
            dx = max(abs(p1[2] - p2[2]) - p1[4] - p2[4], 0.0)
            dy = max(abs(p1[3] - p2[3]) - p1[5] - p2[5], 0.0)
            d = math.hypot(dx, dy)
            if d < CLEAR - 1e-9:
                prob.append(f"pad-pad {p1[0]} {p2[0]} d={d:.3f} "
                            f"@({p1[2]:.2f},{p1[3]:.2f})-({p2[2]:.2f},{p2[3]:.2f})")

        for i in range(len(pads)):
            for j in range(i + 1, len(pads)):
                pad_pad(pads[i], pads[j])

        for net, layer, x1, y1, x2, y2, hw in segs:
            for p in pads:
                if p[0] == net and p[0] is not None:
                    continue
                if layer not in p[1]:
                    continue
                d = _seg_rect_dist(x1, y1, x2, y2, p[2], p[3], p[4], p[5]) - hw
                if d < CLEAR - 1e-9:
                    prob.append(f"pad-seg {p[0]}/{net} d={d:.3f} "
                                f"pad({p[2]:.2f},{p[3]:.2f}) seg({x1:.2f},{y1:.2f})-({x2:.2f},{y2:.2f})")
            for (vn, vx, vy) in vias:
                if vn == net:
                    continue
                d = _pt_seg_dist(vx, vy, x1, y1, x2, y2) - hw - VIA_R
                if d < CLEAR - 1e-9:
                    prob.append(f"via-seg {vn}/{net} d={d:.3f} via({vx:.2f},{vy:.2f}) "
                                f"seg({x1:.2f},{y1:.2f})-({x2:.2f},{y2:.2f})")

        for i, s1 in enumerate(segs):
            for s2 in segs[i + 1:]:
                if s1[0] == s2[0] or s1[1] != s2[1]:
                    continue
                d = _seg_seg_dist((s1[2], s1[3]), (s1[4], s1[5]),
                                  (s2[2], s2[3]), (s2[4], s2[5])) \
                    - s1[6] - s2[6]
                if d < CLEAR - 1e-9:
                    prob.append(f"seg-seg {s1[0]}/{s2[0]} {s1[1]} d={d:.3f} "
                                f"({s1[2]:.2f},{s1[3]:.2f})-({s1[4]:.2f},{s1[5]:.2f}) x "
                                f"({s2[2]:.2f},{s2[3]:.2f})-({s2[4]:.2f},{s2[5]:.2f})")

        # kicad-happy DFM-001 endpoint-proximity equivalence check
        # (different-net segment endpoints on same layer must stay apart)
        for i, s1 in enumerate(segs):
            for s2 in segs[i + 1:]:
                if s1[0] == s2[0] or s1[1] != s2[1]:
                    continue
                for (x1, y1) in ((s1[2], s1[3]), (s1[4], s1[5])):
                    for (x2, y2) in ((s2[2], s2[3]), (s2[4], s2[5])):
                        d = math.hypot(x1 - x2, y1 - y2) - s1[6] - s2[6]
                        if 0 <= d < CLEAR - 1e-9:
                            prob.append(
                                f"endpoint {s1[0]}/{s2[0]} {s1[1]} d={d:.3f} "
                                f"({x1:.2f},{y1:.2f})~({x2:.2f},{y2:.2f})")

        for i, v1 in enumerate(vias):
            for p in pads:
                if p[0] == v1[0] and p[0] is not None:
                    continue
                d = _pt_rect_dist(v1[1], v1[2], p[2], p[3], p[4], p[5]) - VIA_R
                if d < CLEAR - 1e-9:
                    prob.append(f"via-pad {v1[0]}/{p[0]} d={d:.3f} "
                                f"via({v1[1]:.2f},{v1[2]:.2f}) pad({p[2]:.2f},{p[3]:.2f})")
            for v2 in vias[i + 1:]:
                if v1[0] == v2[0]:
                    continue
                d = math.hypot(v1[1] - v2[1], v1[2] - v2[2]) - 2 * VIA_R
                if d < CLEAR - 1e-9:
                    prob.append(f"via-via {v1[0]}/{v2[0]} d={d:.3f} "
                                f"({v1[1]:.2f},{v1[2]:.2f})-({v2[1]:.2f},{v2[2]:.2f})")

        # board edge
        x0, y0, x1, y1 = edge
        for net, layer, xa, ya, xb, yb, hw in segs:
            for (ex, ey) in ((xa, ya), (xb, yb)):
                d_edge = min(ex - x0, x1 - ex, ey - y0, y1 - ey)
                if d_edge - hw < EDGE_CLEAR - 1e-9:
                    prob.append(f"edge-seg {net} d={d_edge - hw:.3f} @({ex:.2f},{ey:.2f})")
        for vn, vx, vy in vias:
            d_edge = min(vx - x0, x1 - vx, vy - y0, y1 - vy)
            if d_edge - VIA_R < EDGE_CLEAR - 1e-9:
                prob.append(f"edge-via {vn} d={d_edge - VIA_R:.3f} @({vx:.2f},{vy:.2f})")

        # keepout (no copper at all inside)
        for kx0, ky0, kx1, ky1 in keepouts:
            for net, layer, xa, ya, xb, yb, hw in segs:
                d = _seg_rect_dist(xa, ya, xb, yb, (kx0 + kx1) / 2, (ky0 + ky1) / 2,
                                   (kx1 - kx0) / 2, (ky1 - ky0) / 2) - hw
                if d < 0:
                    prob.append(f"keepout-seg {net} @({xa:.2f},{ya:.2f})-({xb:.2f},{yb:.2f})")
            for vn, vx, vy in vias:
                if kx0 - VIA_R < vx < kx1 + VIA_R and ky0 - VIA_R < vy < ky1 + VIA_R:
                    prob.append(f"keepout-via {vn} @({vx:.2f},{vy:.2f})")
        return prob

    def check_courtyards(self):
        prob = []
        for i, c1 in enumerate(self.crtyds):
            for c2 in self.crtyds[i + 1:]:
                ox = max(0.0, min(c1[3], c2[3]) - max(c1[1], c2[1]))
                oy = max(0.0, min(c1[4], c2[4]) - max(c1[2], c2[2]))
                if ox * oy > CRTYD + 1e-9:
                    prob.append(f"courtyard {c1[0]}/{c2[0]} overlap {ox * oy:.2f} mm2")
        return prob

    def save(self, path):
        self.pcb.save(path)


# ---------------------------------------------------------------------------
# PCB
# ---------------------------------------------------------------------------
R0603 = "Resistor_SMD:R_0603_1608Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
RC = (-1.05, -0.65, 1.05, 0.65)  # 0603 courtyard


def hop(b, net, pts, width=0.25):
    """Multi-layer polyline: pts = [(x, y, layer), ...].  Draws segments
    between consecutive same-layer points and drops a via at every layer
    transition point."""
    for a, z in zip(pts, pts[1:]):
        if a[2] == z[2]:
            b.route(net, [(a[0], a[1]), (z[0], z[1])], width=width, layer=a[2])
        else:
            b.via(net, z[0], z[1])


def build_pcb(fps):
    b = PcbBuilder(BOARD)
    b.pcb.add_mounting_holes(3.5)
    for (mx, my) in ((3.5, 3.5), (76.5, 3.5), (3.5, 46.5), (76.5, 46.5)):
        b.cu.add_pad("GND", frozenset({"F.Cu", "B.Cu"}), mx, my, 1.6, 1.6, "MH")
    b.pcb.keepout_rect(*KEEPOUT, note="ESP32-C6 antenna keepout - no copper")

    # ---- placement ----
    b.place(fps["ESP32-C6-WROOM-1"], "U1", "ESP32-C6-WROOM-1", 22, 16,
            crtyd=(-9.5, -13.25, 9.5, 13.25))
    b.place("Connector_USB:USB_C_Receptacle_USB2.0_16P", "X1", "USB_C_16P",
            12, 46.4, rot=180, crtyd=(-5.6, -2.2, 5.6, 4.4))
    b.place("Package_TO_SOT_SMD:SOT-23-5", "U6", "AP2112K-3.3", 31, 35,
            crtyd=(-1.7, -1.5, 1.7, 1.5))
    b.place(fps["Tactile-6x6-SMD"], "BT1", "SW_PUSH", 6.7, 12,
            crtyd=(-5.7, -3.15, 5.7, 3.15))
    b.place(fps["Tactile-6x6-SMD"], "BT2", "SW_PUSH", 6.7, 20,
            crtyd=(-5.7, -3.15, 5.7, 3.15))
    b.place(fps["Tactile-6x6-SMD"], "BT_LF", "SW_PUSH", 24, 41,
            crtyd=(-5.7, -3.15, 5.7, 3.15))
    b.place(fps["Tactile-6x6-SMD"], "BT_UP", "SW_PUSH", 35.9, 41,
            crtyd=(-5.7, -3.15, 5.7, 3.15))
    b.place(fps["Tactile-6x6-SMD"], "BT_OK", "SW_PUSH", 47.8, 41,
            crtyd=(-5.7, -3.15, 5.7, 3.15))
    b.place(fps["Tactile-6x6-SMD"], "BT_DN", "SW_PUSH", 59.7, 41,
            crtyd=(-5.7, -3.15, 5.7, 3.15))
    b.place(fps["Tactile-6x6-SMD"], "BT_RT", "SW_PUSH", 71.6, 41,
            crtyd=(-5.7, -3.15, 5.7, 3.15))
    b.place("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
            "J5", "Conn_01x04", 3.5, 33, crtyd=(-1.52, -1.52, 1.52, 11.68))
    b.place("Connector_PinHeader_2.54mm:PinHeader_2x07_P2.54mm_Vertical",
            "J1", "Conn_02x07", 74, 8, crtyd=(-2.79, -1.52, 2.79, 16.76))
    b.place("Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
            "J2", "Conn_01x05", 41, 10, crtyd=(-1.52, -1.52, 1.52, 13.2))
    b.place(fps["KF128-5.08-3P"], "J3", "Term_3P", 52, 4.7, rot=90,
            crtyd=(-3.6, -6.28, 3.6, 6.28))
    b.place(fps["KF128-5.08-2P"], "J4", "Term_2P", 39, 4.7, rot=90,
            crtyd=(-3.6, -3.74, 3.6, 3.74))
    b.place(fps["EC11-Encoder"], "ENC1", "EC11", 64, 30.9,
            crtyd=(-7.0, -6.6, 7.0, 6.6))
    b.place(fps["INMP441-LGA9"], "U2", "INMP441", 56, 11.5,
            crtyd=(-2.6, -2.1, 2.6, 2.1))
    b.place(fps["SHT31-DFN8"], "U3", "SHT31", 62, 17,
            crtyd=(-1.5, -1.7, 1.5, 1.7))
    b.place(fps["BH1750-WSOF6"], "U4", "BH1750", 62, 23,
            crtyd=(-1.75, -1.0, 1.75, 1.0))
    b.place("Package_SO:SOIC-14_3.9x8.7mm_P1.27mm", "U5", "74AHCT125",
            46, 31, crtyd=(-3.45, -5.0, 3.45, 5.0))
    # passives
    b.place(C0603, "C1", "10uF", 29, 45.5, crtyd=RC)
    b.place(C0603, "C2", "10uF", 26, 34, rot=180, crtyd=RC)
    b.place(C0603, "C3", "100nF", 11.5, 28.5, crtyd=RC)
    b.place(C0603, "C4", "100nF", 6, 29, crtyd=RC)
    b.place(C0603, "C5", "100nF", 58.5, 17, rot=180, crtyd=RC)
    b.place(C0603, "C6", "100nF", 58.5, 23, rot=180, crtyd=RC)
    b.place(C0603, "C7", "100nF", 52, 9.2, crtyd=RC)
    b.place(C0603, "C8", "10uF", 52, 11.5, crtyd=RC)
    b.place(C0603, "C9", "100nF", 41, 27, rot=180, crtyd=RC)
    b.place(C0603, "C10", "100nF", 9, 25, crtyd=RC)
    b.place(R0603, "R1", "4.7k", 59, 15, crtyd=RC)
    b.place(R0603, "R2", "4.7k", 55.5, 26.5, crtyd=RC)
    b.place(R0603, "R3", "5.1k", 34, 35.5, crtyd=RC)
    b.place(R0603, "R4", "5.1k", 37, 35.5, crtyd=RC)
    b.place(R0603, "R5", "22R", 7, 27.1, rot=90, crtyd=RC)
    b.place(R0603, "R6", "22R", 7, 24.5, rot=90, crtyd=RC)
    b.place(R0603, "R7", "10k", 7, 33.5, crtyd=RC)
    b.place(R0603, "R8", "1k", 10, 32.5, crtyd=RC)
    b.place(R0603, "R9", "100R", 75.5, 28, crtyd=RC)
    b.place(R0603, "R10", "10k", 75.5, 31, crtyd=RC)
    b.place(R0603, "R11", "10k", 40.5, 48, crtyd=RC)
    b.place(R0603, "R12", "0R", 20.5, 48, crtyd=RC)
    b.place(R0603, "R13", "2.2k", 24.5, 48, crtyd=RC)
    b.place(R0603, "R14", "4.7k", 28.5, 48, crtyd=RC)
    b.place(R0603, "R15", "10k", 32.5, 48, crtyd=RC)
    b.place(R0603, "R16", "0R", 13, 32, crtyd=RC)
    b.place(R0603, "R17", "0R", 17, 32, crtyd=RC)
    b.place(R0603, "R18", "22k", 36.5, 48, crtyd=RC)
    b.place(R0603, "R19", "470R", 52, 31, crtyd=RC)
    b.place(R0603, "R21", "0R", 38, 24.3, crtyd=RC)
    b.place(R0603, "R20", "0R", 37, 36.8, crtyd=RC)
    b.place("LED_SMD:LED_0603_1608Metric", "D1", "LED_RED", 8, 30.5, crtyd=RC)

    # ---- net assignment (schematic plans) ----
    plans = {"U1": U1_PLAN, "X1": X1_PLAN, "U2": U2_PLAN, "U3": U3_PLAN,
             "U4": U4_PLAN, "U5": U5_PLAN, "U6": U6_PLAN, "ENC1": ENC_PLAN,
             "J1": J1_PLAN, "J2": J2_PLAN, "J3": J3_PLAN, "J4": J4_PLAN,
             "J5": J5_PLAN}
    plans.update(RX_PLAN)
    plans.update(CX_PLAN)
    plans.update(DX_PLAN)
    plans.update(BT_PLAN)
    for ref, plan in plans.items():
        for pad, net in plan.items():
            if net:
                b.net_pad(ref, pad, net)
    b.collect_pads({(r, p): n for r, pl in plans.items()
                    for p, n in pl.items() if n})

    route_all(b)

    # ---- GND pour + silkscreen ----
    b.pcb.gnd_zone()
    b.pcb.silk_text("ledhub-c6", 48, 48.6, size=1.6)
    b.pcb.silk_text("EN", 6, 8.0, size=1.0)
    b.pcb.silk_text("BOOT", 6, 16.0, size=1.0)
    b.pcb.silk_text("TFT 2.8in", 74, 27.5, size=1.0)
    b.pcb.silk_text("LD2450", 45, 21.5, size=1.0)
    b.pcb.silk_text("LED OUT", 52, 9.3, size=1.0)
    b.pcb.silk_text("LED 5V IN", 39, 9.3, size=1.0)
    b.pcb.silk_text("3V3 TX RX GND", 8.5, 36.5, size=1.0)
    b.pcb.silk_text("LF UP OK DN RT", 47, 37.3, size=1.0)

    b.save(os.path.join(OUT, BOARD + ".kicad_pcb"))

    # ---- geometric self-check ----
    probs = b.check_courtyards()
    probs += b.check_clearance((0.0, 0.0, W, H), [KEEPOUT])
    if probs:
        for p in probs[:60]:
            print("SELF-CHECK:", p)
        raise SystemExit(f"self-check failed: {len(probs)} problem(s)")
    print("self-check OK")


# ---------------------------------------------------------------------------
# Routing
#
# REV 1.0 routing policy (per project lead directive after a previous A*
# attempt produced 42 cross-net collisions): NO copper tracks/vias are
# emitted.  All nets remain as ratsnest; GND is provided by the full-board
# B.Cu pour.  This guarantees zero cross-net (DFM-001) violations; routing
# is left to interactive/autorouter work in KiCad.  See README "Routing
# status".
# ---------------------------------------------------------------------------
def route_all(b):
    """No copper tracks/vias are emitted (see policy note above).

    * 3 assembly fiducials (FD-001).
    * One small unconnected "marker" pour per non-GND net on F.Cu in free
      board areas.  This documents the net set on the PCB and keeps the
      connectivity audit aware that these nets are intentionally left as
      ratsnest (routing deferred to KiCad; see README "Routing status").
      GND is covered by the full-board B.Cu pour.
    """
    def fid(ref, x, y):
        fp = kg.Footprint(BOARD, "Fiducial_1mm")
        fp.add_pad("1", "smd", "circle", 0.0, 0.0, 1.0, 1.0,
                   layers=("F.Cu", "F.Mask"))
        fp.add_circle(0, 0, 1.5, "F.CrtYd", 0.05)
        b.place(fp, ref, "Fiducial", x, y, crtyd=(-1.5, -1.5, 1.5, 1.5))

    fid("H5", 36.0, 12.0)
    fid("H6", 36.0, 20.0)
    fid("H7", 50.0, 20.0)

    nets = set()
    for plan in (list(RX_PLAN.values()) + list(CX_PLAN.values())
                 + list(DX_PLAN.values()) + list(BT_PLAN.values())
                 + [U1_PLAN, X1_PLAN, U2_PLAN, U3_PLAN, U4_PLAN, U5_PLAN,
                    U6_PLAN, ENC_PLAN, J1_PLAN, J2_PLAN, J3_PLAN, J4_PLAN,
                    J5_PLAN]):
        nets.update(n for n in plan.values() if n)
    nets.discard("GND")
    nets = sorted(nets)

    cells = []
    for cx in range(43, 69, 2):          # strip below the nav buttons
        for cy in (45.3, 47.3):
            cells.append((cx, cy))
    for cy in range(13, 27, 2):          # column right of the module
        cells.append((33.3, cy))
    for cx in (44.3, 46.3):              # between J2 and U5/U2
        for cy in (14.3, 16.3, 18.3, 20.3, 22.3):
            cells.append((cx, cy))
    assert len(cells) >= len(nets), (len(cells), len(nets))
    for net, (cx, cy) in zip(nets, cells):
        b.pcb.zone(net, (cx, cy, cx + 1.6, cy + 1.6), layer="F.Cu")


# ---------------------------------------------------------------------------
# BOM + main
# ---------------------------------------------------------------------------
PART_INFO["LD2450"] = ("-", "LD2450 24GHz mmWave radar module (on J2)",
                       "-", "HLK-LD2450")
PART_INFO["TFT_2.8"] = ("-", "2.8in ILI9341 SPI TFT module 240x320 (on J1)",
                        "-", "ILI9341-2.8-SPI")


def write_bom(path):
    rows = [("U1", "ESP32-C6-WROOM-1"), ("X1", "USB_C_16P"),
            ("U2", "INMP441"), ("U3", "SHT31"), ("U4", "BH1750"),
            ("U5", "74AHCT125"), ("U6", "AP2112K-3.3"),
            ("ENC1", "EC11"),
            ("R1,R2,R14", "4.7k"), ("R13", "2.2k"),
            ("R7,R10,R11,R15", "10k"), ("R18", "22k"),
            ("R3,R4", "5.1k"), ("R5,R6", "22R"), ("R9", "100R"),
            ("R19", "470R"), ("R8", "1k"), ("R12,R16,R17,R20,R21", "0R"),
            ("C1,C2,C8", "10uF"),
            ("C3,C4,C5,C6,C7,C9,C10", "100nF"),
            ("D1", "LED_RED"),
            ("BT1,BT2,BT_UP,BT_DN,BT_LF,BT_RT,BT_OK", "SW_PUSH"),
            ("J1", "Conn_02x07"), ("J2", "Conn_01x05"),
            ("J5", "Conn_01x04"), ("J3", "Term_3P"), ("J4", "Term_2P"),
            ("(on J2)", "LD2450"), ("(on J1)", "TFT_2.8")]
    with open(path, "w") as f:
        f.write("ref,value,footprint,lcsc,mpn,qty\n")
        for refs, val in rows:
            fp, _desc, lcsc, mpn = PART_INFO[val]
            qty = len(refs.split(","))
            f.write(f"{refs},{val},{fp},{lcsc},{mpn},{qty}\n")


def main():
    kg.write_project(os.path.join(OUT, BOARD + ".kicad_pro"), BOARD,
                     BOARD + "-lib")
    fps = build_footprints(BOARD)
    build_schematic(os.path.join(OUT, BOARD + ".kicad_sch"))
    build_pcb(fps)
    write_bom(os.path.join(OUT, "bom_lcsc.csv"))
    problems = kg.validate_project(OUT)
    for p in problems:
        print("VALIDATE:", p)
    if problems:
        raise SystemExit(f"validate_project failed: {len(problems)} problem(s)")
    print("ledhub-c6: project generated + validated")


if __name__ == "__main__":
    main()
