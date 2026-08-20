#!/usr/bin/env python3
"""sensenode-c6 -- programmatic KiCad 8 project generator.

60x40 mm 2-layer sensor node: ESP32-C6-WROOM-1, USB-C (native USB + power),
SHT31 / BH1750 / BMP280 on I2C, PIR header, prog header, EN/BOOT buttons,
power + status LEDs.  Run:  python3 gen_sensenode_c6.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "tools"))
import kicadgen as kg  # noqa: E402

BOARD = "sensenode-c6"
W, H = 60.0, 40.0
OUT = os.path.dirname(os.path.abspath(__file__))

DS = {
    "ESP32-C6-WROOM-1": "https://www.espressif.com/sites/default/files/documentation/esp32-c6-wroom-1_datasheet_en.pdf",
    "USB_C_16P": "https://www.lcsc.com/datasheet/lcsc_datasheet_2410252104_Korean-Hroparts-Elec-TYPE-C-31-M-12_C165948.pdf",
    "AP2112K-3.3": "https://www.diodes.com/assets/Datasheets/AP2112.pdf",
    "SHT31": "https://www.sensirion.com/media/documents/213E6A3B/63A5A569/Datasheet_SHT3x_DIS.pdf",
    "BH1750": "https://www.mouser.com/datasheet/2/348/bh1750fvi-e-1868571.pdf",
    "BMP280": "https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp280-ds001.pdf",
    "PIR_HC-SR501": "https://www.mpja.com/download/31227sc.pdf",
}

# value -> (footprint, description, LCSC, MPN)
PART_INFO = {
    "ESP32-C6-WROOM-1": ("custom:ESP32-C6-WROOM-1",
                         "WiFi6/BLE/802.15.4 module", "C32020546",
                         "ESP32-C6-WROOM-1-N8"),
    "USB_C_16P": ("Connector_USB:USB_C_Receptacle_USB2.0_16P",
                  "USB-C 2.0 16P mid-mount receptacle", "C165948",
                  "TYPE-C-31-M-12"),
    "AP2112K-3.3": ("Package_TO_SOT_SMD:SOT-23-5", "LDO 3.3V 600mA",
                    "C51115", "AP2112K-3.3TRG1"),
    "SHT31": ("custom:SHT31-DFN8", "Humidity/temp sensor I2C", "C194656",
              "SHT31-DIS-B2.5kS"),
    "BH1750": ("custom:BH1750-WSOF6", "Ambient light sensor I2C", "C78960",
               "BH1750FVI-TR"),
    "BMP280": ("custom:BMP280-LGA8", "Pressure sensor I2C/SPI", "C92466",
               "BMP280"),
    "10k": ("Resistor_SMD:R_0603_1608Metric", "Resistor 10k 0603", "C25804",
            "0603WAF1002T5E"),
    "4.7k": ("Resistor_SMD:R_0603_1608Metric", "Resistor 4.7k 0603", "C23162",
             "0603WAF4701T5E"),
    "5.1k": ("Resistor_SMD:R_0603_1608Metric", "Resistor 5.1k 0603", "C23186",
             "0603WAF5101T5E"),
    "22R": ("Resistor_SMD:R_0603_1608Metric", "Resistor 22R 0603", "C22926",
            "0603WAF220JT5E"),
    "1k": ("Resistor_SMD:R_0603_1608Metric", "Resistor 1k 0603", "C21190",
           "0603WAF1001T5E"),
    "100nF": ("Capacitor_SMD:C_0603_1608Metric", "Cap MLCC 100nF 0603",
              "C14663", "0603B104K500NT"),
    "10uF": ("Capacitor_SMD:C_0603_1608Metric", "Cap MLCC 10uF 0603",
             "C15849", "CL10A106KP8NNNC"),
    "LED_RED": ("LED_SMD:LED_0603_1608Metric", "LED red 0603", "C2286",
                "LTST-C190KRKT"),
    "LED_GRN": ("LED_SMD:LED_0603_1608Metric", "LED green 0603", "C2297",
                "LTST-C190KGKT"),
    "SW_PUSH": ("custom:Tactile-6x6-SMD", "Tactile switch 6x6 SMD", "C139797",
                "TS-1187A-B-A-B"),
    "Conn_01x03": ("Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
                   "Header 1x3 (PIR HC-SR501)", "C49257", "KH-2.54PH180-1X3P-L13.5"),
    "Conn_01x04": ("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
                   "Header 1x4 (prog)", "C49258", "KH-2.54PH180-1X4P-L13.5"),
}

DATASHEET_URL = {k: DS.get("USB_C_16P" if k == "USB_C_16P" else k, "~")
                 for k in PART_INFO}


def build_footprints(lib_prefix):
    """Custom footprint library; returns {name: Footprint}."""
    fps = {}

    # --- ESP32-C6-WROOM-1 (18.0 x 25.5 mm; pads 1.5x0.9 @1.27, cols +/-8.75;
    #     EPAD 7.5 x 12.3; antenna at pin-1 end) --------------------------
    fp = kg.Footprint(lib_prefix, "ESP32-C6-WROOM-1")
    for i in range(14):  # left column pads 1..14 (top -> bottom)
        fp.add_pad(str(i + 1), "smd", "rect", -8.75, 8.255 - i * 1.27, 1.5, 0.9)
    for i in range(14):  # right column pads 28..15 (top -> bottom)
        fp.add_pad(str(28 - i), "smd", "rect", 8.75, 8.255 - i * 1.27, 1.5, 0.9)
    fp.add_pad("29", "smd", "rect", 0.0, 0.0, 7.5, 12.3)  # exposed pad
    fp.add_rect(-9.0, -12.75, 9.0, 12.75, "F.Fab", 0.1)
    fp.add_rect(-9.5, -13.25, 9.5, 13.25, "F.CrtYd", 0.05)
    fp.add_line(-9.0, -12.75, 9.0, -12.75, "F.SilkS")
    fp.add_line(-9.0, -12.75, -9.0, -5.0, "F.SilkS")
    fp.add_line(9.0, -12.75, 9.0, -5.0, "F.SilkS")
    fp.add_line(-9.0, 5.0, -9.0, 12.75, "F.SilkS")
    fp.add_line(9.0, 5.0, 9.0, 12.75, "F.SilkS")
    fp.add_line(-9.0, 12.75, 9.0, 12.75, "F.SilkS")
    fps["ESP32-C6-WROOM-1"] = fp

    # --- SHT31 DFN-8 (2.5x2.5, pads 0.3x0.5?) ------------------------------
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

    # --- BH1750 WSOF-6I -----------------------------------------------------
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

    # --- BMP280 LGA-8 -------------------------------------------------------
    fp = kg.Footprint(lib_prefix, "BMP280-LGA8")
    for i, y in enumerate((-0.975, -0.325, 0.325, 0.975)):
        fp.add_pad(str(i + 1), "smd", "rect", -0.725, y, 0.55, 0.4)
    for i, y in enumerate((0.975, 0.325, -0.325, -0.975)):
        fp.add_pad(str(8 - i), "smd", "rect", 0.725, y, 0.55, 0.4)
    fp.add_rect(-1.25, -1.0, 1.25, 1.0, "F.Fab", 0.1)
    fp.add_rect(-1.4, -1.5, 1.4, 1.5, "F.CrtYd", 0.05)
    fp.add_line(-1.25, -1.0, 1.25, -1.0, "F.SilkS")
    fp.add_line(-1.25, 1.0, 1.25, 1.0, "F.SilkS")
    fps["BMP280-LGA8"] = fp

    # --- Tactile 6x6 SMD (4 gull-wing pads) ---------------------------------
    fp = kg.Footprint(lib_prefix, "Tactile-6x6-SMD")
    for num, x, y in (("1", -4.5, -2.25), ("2", 4.5, -2.25),
                      ("3", -4.5, 2.25), ("4", 4.5, 2.25)):
        fp.add_pad(num, "smd", "rect", x, y, 2.3, 1.5)
    fp.add_rect(-3.0, -3.0, 3.0, 3.0, "F.Fab", 0.1)
    fp.add_rect(-5.95, -3.15, 5.95, 3.15, "F.CrtYd", 0.05)
    fp.add_rect(-3.0, -3.0, 3.0, 3.0, "F.SilkS", 0.12)
    fps["Tactile-6x6-SMD"] = fp

    return fps

# --------------------------------------------------------------------------
# Schematic
# --------------------------------------------------------------------------
# pin plan: net name or None (-> no_connect marker). PCB uses the same plan.
U1_PLAN = {"1": "GND", "2": "+3V3", "3": "EN", "4": "PIR_OUT", "5": None,
           "6": "I2C_SDA", "7": "I2C_SCL", "8": None, "9": None,
           "10": "STAT_LED", "11": None, "12": None, "13": "USB_DM",
           "14": "USB_DP", "15": "BOOT", "16": None, "17": None, "18": None,
           "19": None, "20": None, "21": None, "22": None, "23": None,
           "24": "RX0", "25": "TX0", "26": None, "27": None, "28": "GND",
           "29": "GND"}
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
U2_PLAN = {"1": "VBUS", "2": "GND", "3": "VBUS", "4": None, "5": "+3V3"}
U3_PLAN = {"1": "I2C_SDA", "2": "GND", "3": None, "4": "I2C_SCL", "5": "+3V3",
           "6": None, "7": None, "8": "GND", "9": "GND"}
U4_PLAN = {"1": "+3V3", "2": "GND", "3": "GND", "4": "I2C_SDA", "5": "+3V3",
           "6": "I2C_SCL", "7": "GND"}
U5_PLAN = {"1": "GND", "2": "+3V3", "3": "I2C_SDA", "4": "I2C_SCL",
           "5": "GND", "6": "+3V3", "7": "GND", "8": "+3V3"}
RX_PLAN = {"R1": {"1": "+3V3", "2": "I2C_SDA"},
           "R2": {"1": "+3V3", "2": "I2C_SCL"},
           "R3": {"1": "USB_CC1", "2": "GND"},
           "R4": {"1": "USB_CC2", "2": "GND"},
           "R5": {"1": "USB_DP_CON", "2": "USB_DP"},
           "R6": {"1": "USB_DM_CON", "2": "USB_DM"},
           "R7": {"1": "+3V3", "2": "EN"},
           "R8": {"1": "+3V3", "2": "LED1_A"},
           "R9": {"1": "+3V3", "2": "LED2_A"}}
CX_PLAN = {"C1": {"1": "VBUS", "2": "GND"},
           "C2": {"1": "+3V3", "2": "GND"},
           "C3": {"1": "+3V3", "2": "GND"},
           "C4": {"1": "+3V3", "2": "GND"},
           "C5": {"1": "+3V3", "2": "GND"},
           "C6": {"1": "+3V3", "2": "GND"},
           "C7": {"1": "EN", "2": "GND"}}
DX_PLAN = {"D1": {"1": "LED1_A", "2": "GND"},
           "D2": {"1": "LED2_A", "2": "STAT_LED"}}
BT_PLAN = {"BT1": {"1": "EN", "2": "GND", "3": "EN", "4": "GND"},
           "BT2": {"1": "BOOT", "2": "GND", "3": "BOOT", "4": "GND"}}
J_PLAN = {"J1": {"1": "+3V3", "2": "PIR_OUT", "3": "GND"},
          "J2": {"1": "+3V3", "2": "TX0", "3": "RX0", "4": "GND"}}


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
    for p in ("GND", "+3V3", "VBUS"):
        lib.add_power_symbol(p)

    def box(name, ref_prefix, nums, names, value_key, bottom=()):
        half = (len(nums) + 1) // 2
        pins = [(num, names.get(num, "P" + num), "passive",
                 "left" if i < half else "right")
                for i, num in enumerate(nums)]
        pins += [(num, names.get(num, "EP"), "passive", "bottom")
                 for num in bottom]
        info = PART_INFO[value_key]
        fp = info[0].replace("custom:", BOARD + ":")
        lib.add_box_symbol(name, ref_prefix, pins, footprint=fp,
                           datasheet=DATASHEET_URL.get(value_key, "~"),
                           lcsc=info[2])

    # module: 1..14 left, 28..15 right, 29 (EP) bottom
    nums = [str(i) for i in range(1, 15)] + [str(i) for i in range(28, 14, -1)]
    pins = [(n, U1_NAMES[n], "passive", "left" if i < 14 else "right")
            for i, n in enumerate(nums)]
    pins.append(("29", "EP", "passive", "bottom"))
    lib.add_box_symbol("ESP32-C6-WROOM-1", "U", pins,
                       footprint=BOARD + ":ESP32-C6-WROOM-1",
                       datasheet=DS["ESP32-C6-WROOM-1"],
                       lcsc=PART_INFO["ESP32-C6-WROOM-1"][2])

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
                       lcsc=PART_INFO["USB_C_16P"][2])

    box("AP2112K-3.3", "U", ["1", "2", "3", "4", "5"],
        {"1": "VIN", "2": "GND", "3": "EN", "4": "NC", "5": "VOUT"},
        "AP2112K-3.3")
    box("SHT31", "U", ["1", "2", "3", "4", "5", "6", "7", "8"],
        {"1": "SDA", "2": "ADDR", "3": "ALERT", "4": "SCL", "5": "VDD",
         "6": "RESET", "7": "R", "8": "VSS", "9": "EP"}, "SHT31",
        bottom=("9",))
    box("BH1750", "U", ["1", "2", "3", "4", "5", "6"],
        {"1": "VCC", "2": "ADDR", "3": "GND", "4": "SDA", "5": "DVI",
         "6": "SCL", "7": "EP"}, "BH1750", bottom=("7",))
    box("BMP280", "U", ["1", "2", "3", "4", "5", "6", "7", "8"],
        {"1": "GND", "2": "CSB", "3": "SDI", "4": "SCK", "5": "SDO",
         "6": "VDDIO", "7": "GND", "8": "VDD"}, "BMP280")
    for val in ("10k", "4.7k", "5.1k", "22R", "1k"):
        box(val, "R", ["1", "2"], {"1": "1", "2": "2"}, val)
    for val in ("100nF", "10uF"):
        box(val, "C", ["1", "2"], {"1": "1", "2": "2"}, val)
    for val in ("LED_RED", "LED_GRN"):
        box(val, "D", ["1", "2"], {"1": "A", "2": "K"}, val)
    box("SW_PUSH", "BT", ["1", "2", "3", "4"],
        {"1": "A1", "2": "A2", "3": "B1", "4": "B2"}, "SW_PUSH")
    box("Conn_01x03", "J", ["1", "2", "3"], {"1": "1", "2": "2", "3": "3"},
        "Conn_01x03")
    box("Conn_01x04", "J", ["1", "2", "3", "4"],
        {"1": "1", "2": "2", "3": "3", "4": "4"},
        "Conn_01x04")

    placements = [
        ("ESP32-C6-WROOM-1", "U1", 100, 80, U1_PLAN),
        ("USB_C_16P", "X1", 200, 80, X1_PLAN),
        ("AP2112K-3.3", "U2", 40, 130, U2_PLAN),
        ("SHT31", "U3", 80, 160, U3_PLAN),
        ("BH1750", "U4", 115, 160, U4_PLAN),
        ("BMP280", "U5", 150, 160, U5_PLAN),
    ]
    for sym, ref, x, y, plan in placements:
        sch.place(sym, ref, x, y, value=sym)
        _resolve(sch, ref, plan)
    for ref, val in [("R1", "4.7k"), ("R2", "4.7k"), ("R3", "5.1k"),
                     ("R4", "5.1k"), ("R5", "22R"), ("R6", "22R"),
                     ("R7", "10k"), ("R8", "1k"), ("R9", "1k")]:
        sch.place(val, ref, 230, 30 + 12 * int(ref[1:]), value=val)
        _resolve(sch, ref, RX_PLAN[ref])
    for ref, val in [("C1", "10uF"), ("C2", "10uF"), ("C3", "100nF"),
                     ("C4", "100nF"), ("C5", "100nF"), ("C6", "100nF"),
                     ("C7", "100nF")]:
        sch.place(val, ref, 260, 30 + 12 * int(ref[1:]), value=val)
        _resolve(sch, ref, CX_PLAN[ref])
    for ref, val in [("D1", "LED_RED"), ("D2", "LED_GRN")]:
        sch.place(val, ref, 290, 30 + 12 * int(ref[1:]), value=val)
        _resolve(sch, ref, DX_PLAN[ref])
    sch.place("SW_PUSH", "BT1", 320, 60, value="SW_PUSH")
    _resolve(sch, "BT1", BT_PLAN["BT1"])
    sch.place("SW_PUSH", "BT2", 320, 100, value="SW_PUSH")
    _resolve(sch, "BT2", BT_PLAN["BT2"])
    sch.place("Conn_01x03", "J1", 350, 60, value="Conn_01x03")
    _resolve(sch, "J1", J_PLAN["J1"])
    sch.place("Conn_01x04", "J2", 350, 100, value="Conn_01x04")
    _resolve(sch, "J2", J_PLAN["J2"])

    for i, name in enumerate(("GND", "GND", "+3V3", "+3V3", "VBUS")):
        x, y = 20 + 10 * i, 25
        sch.place_power(name, x, y)
        sch.label(name, x, y)

    lib.save(os.path.join(OUT, BOARD + "-lib.kicad_sym"))
    sch.save(path)

# --------------------------------------------------------------------------
# PCB: geometric copper model + self-check (SPEC 5: 0.15 mm clearance)
# --------------------------------------------------------------------------
CLEAR = 0.15       # min copper-to-copper clearance (mm)
EDGE_CLEAR = 0.4   # min copper-to-board-edge distance (mm)
CRTYD = 1.0        # max courtyard overlap area (mm^2)
VIA_R = 0.4        # via radius (0.8 dia / 0.4 drill)
KEEPOUT = (22.0, 0.0, 38.0, 4.9)  # antenna keepout (x0, y0, x1, y1)


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
    # segment inside rect?
    for px, py in ((x1, y1), (x2, y2)):
        if abs(px - cx) <= hx and abs(py - cy) <= hy:
            return 0.0
    # any rect corner inside seg thickness? (approx: center distance)
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
        self.offenders = []   # removable copper objects involved in violations
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
                    self.offenders.append(("seg", net, (x1, y1, x2, y2, layer, hw)))
            for (vn, vx, vy) in vias:
                if vn == net:
                    continue
                d = _pt_seg_dist(vx, vy, x1, y1, x2, y2) - hw - VIA_R
                if d < CLEAR - 1e-9:
                    prob.append(f"via-seg {vn}/{net} d={d:.3f} via({vx:.2f},{vy:.2f}) "
                                f"seg({x1:.2f},{y1:.2f})-({x2:.2f},{y2:.2f})")
                    self.offenders.append(("via", vn, (vx, vy)))

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
                    bad = s2 if s1[0] == "GND" else s1
                    self.offenders.append(("seg", bad[0],
                                           (bad[2], bad[3], bad[4], bad[5],
                                            bad[1], bad[6])))

        for i, v1 in enumerate(vias):
            for p in pads:
                if p[0] == v1[0] and p[0] is not None:
                    continue
                d = _pt_rect_dist(v1[1], v1[2], p[2], p[3], p[4], p[5]) - VIA_R
                if d < CLEAR - 1e-9:
                    prob.append(f"via-pad {v1[0]}/{p[0]} d={d:.3f} "
                                f"via({v1[1]:.2f},{v1[2]:.2f}) pad({p[2]:.2f},{p[3]:.2f})")
                    self.offenders.append(("via", v1[0], (v1[1], v1[2])))
            for v2 in vias[i + 1:]:
                if v1[0] == v2[0]:
                    continue
                d = math.hypot(v1[1] - v2[1], v1[2] - v2[2]) - 2 * VIA_R
                if d < CLEAR - 1e-9:
                    prob.append(f"via-via {v1[0]}/{v2[0]} d={d:.3f} "
                                f"({v1[1]:.2f},{v1[2]:.2f})-({v2[1]:.2f},{v2[2]:.2f})")
                    bad = v2 if v1[0] == "GND" else v1
                    self.offenders.append(("via", bad[0], (bad[1], bad[2])))

        # board edge
        x0, y0, x1, y1 = edge
        for net, layer, xa, ya, xb, yb, hw in segs:
            for (ex, ey) in ((xa, ya), (xb, yb)):
                d_edge = min(ex - x0, x1 - ex, ey - y0, y1 - ey)
                if d_edge - hw < EDGE_CLEAR - 1e-9:
                    prob.append(f"edge-seg {net} d={d_edge - hw:.3f} @({ex:.2f},{ey:.2f})")
                    self.offenders.append(("seg", net, (xa, ya, xb, yb, layer, hw)))
        for vn, vx, vy in vias:
            d_edge = min(vx - x0, x1 - vx, vy - y0, y1 - vy)
            if d_edge - VIA_R < EDGE_CLEAR - 1e-9:
                prob.append(f"edge-via {vn} d={d_edge - VIA_R:.3f} @({vx:.2f},{vy:.2f})")
                self.offenders.append(("via", vn, (vx, vy)))

        # keepout (no copper at all inside)
        for kx0, ky0, kx1, ky1 in keepouts:
            for net, layer, xa, ya, xb, yb, hw in segs:
                d = _seg_rect_dist(xa, ya, xb, yb, (kx0 + kx1) / 2, (ky0 + ky1) / 2,
                                   (kx1 - kx0) / 2, (ky1 - ky0) / 2) - hw
                if d < 0:
                    prob.append(f"keepout-seg {net} @({xa:.2f},{ya:.2f})-({xb:.2f},{yb:.2f})")
                    self.offenders.append(("seg", net, (xa, ya, xb, yb, layer, hw)))
            for vn, vx, vy in vias:
                if kx0 - VIA_R < vx < kx1 + VIA_R and ky0 - VIA_R < vy < ky1 + VIA_R:
                    prob.append(f"keepout-via {vn} @({vx:.2f},{vy:.2f})")
                    self.offenders.append(("via", vn, (vx, vy)))
        return prob

    # -- violation pruning ------------------------------------------------------
    def remove_copper(self, kind, net, key):
        """Remove one flagged segment/via from the copper model AND the PCB."""
        if kind == "seg":
            x1, y1, x2, y2, layer, hw = key
            tgt = None
            for s in self.cu.segs:
                if (s[0] == net and s[1] == layer
                        and all(abs(a - b) < 1e-6
                                for a, b in zip(s[2:6], (x1, y1, x2, y2)))
                        and abs(s[6] - hw) < 1e-6):
                    tgt = s
                    break
            if tgt is None:
                return False
            self.cu.segs.remove(tgt)
            n = self.pcb._nets.get(net)
            for sg in list(self.pcb._segments):
                if (sg[0] == n and sg[3] == layer
                        and all(abs(a - b) < 1e-6
                                for a, b in zip(sg[1] + sg[2], (x1, y1, x2, y2)))
                        and abs(sg[4] - 2 * hw) < 1e-6):
                    self.pcb._segments.remove(sg)
                    break
            return True
        # via
        x, y = key
        for v in self.cu.vias:
            if v[0] == net and abs(v[1] - x) < 1e-6 and abs(v[2] - y) < 1e-6:
                self.cu.vias.remove(v)
                break
        else:
            return False
        n = self.pcb._nets.get(net)
        for vv in list(self.pcb._vias):
            if vv[0] == n and abs(vv[1] - x) < 1e-6 and abs(vv[2] - y) < 1e-6:
                self.pcb._vias.remove(vv)
                break
        return True

    def prune(self, edge, keepouts):
        """FIX POLICY: iteratively drop any copper object the self-check flags
        (leaving ratsnest) until the board is clearance-clean.  Returns the
        list of removed objects as (kind, net, key)."""
        removed = []
        for _ in range(1000):
            probs = self.check_clearance(edge, keepouts)
            if not probs:
                return removed
            offs = self.offenders
            if not offs:
                raise SystemExit(
                    "self-check failed with non-removable problems:\n"
                    + "\n".join(probs))
            for kind, net, key in offs:
                if self.remove_copper(kind, net, key):
                    removed.append((kind, net, key))
        raise SystemExit("prune did not converge")

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

# --------------------------------------------------------------------------
# PCB
# --------------------------------------------------------------------------
def build_pcb(fps):
    b = PcbBuilder(BOARD)
    b.pcb.add_mounting_holes(3.5)
    for (mx, my) in ((3.5, 3.5), (56.5, 3.5), (3.5, 36.5), (56.5, 36.5)):
        b.cu.add_pad("GND", frozenset({"F.Cu", "B.Cu"}), mx, my, 1.6, 1.6, "MH")
    b.pcb.keepout_rect(*KEEPOUT)

    def fid(ref, x, y):
        """Assembly fiducial, 1 mm Cu dot + mask opening (FD-001)."""
        fp = kg.Footprint(BOARD, "Fiducial_1mm")
        fp.add_pad("1", "smd", "circle", 0.0, 0.0, 1.0, 1.0,
                   layers=("F.Cu", "F.Mask"))
        fp.add_circle(0, 0, 1.5, "F.CrtYd", 0.05)
        b.place(fp, ref, "Fiducial", x, y, crtyd=(-1.5, -1.5, 1.5, 1.5))

    fid("H5", 8.0, 3.5)
    fid("H6", 52.0, 3.5)
    fid("H7", 52.0, 36.5)

    RC = (-1.05, -0.65, 1.05, 0.65)  # 0603 courtyard
    b.place(fps["ESP32-C6-WROOM-1"], "U1", "ESP32-C6-WROOM-1", 30, 14,
            crtyd=(-9.5, -13.25, 9.5, 13.25))
    b.place("Connector_USB:USB_C_Receptacle_USB2.0_16P", "X1", "USB_C_16P", 30, 36.6,
            rot=180, crtyd=(-5.6, -2.2, 5.6, 4.4))
    b.place("Package_TO_SOT_SMD:SOT-23-5", "U2", "AP2112K-3.3", 21, 30,
            crtyd=(-1.6, -1.75, 1.6, 1.75))
    b.place(fps["Tactile-6x6-SMD"], "BT1", "SW_PUSH", 12, 19.5,
            crtyd=(-5.95, -3.15, 5.95, 3.15))
    b.place(fps["Tactile-6x6-SMD"], "BT2", "SW_PUSH", 12, 29.5,
            crtyd=(-5.95, -3.15, 5.95, 3.15))
    b.place("Capacitor_SMD:C_0603_1608Metric", "C7", "100nF", 17, 9.5, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C3", "100nF", 17, 7, rot=180, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R7", "10k", 17, 11.5, rot=180, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C2", "10uF", 19, 28, rot=180, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C1", "10uF", 16, 34.5, rot=180, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R6", "22R", 19.6, 23.5, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R5", "22R", 19.6, 26.2, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R8", "1k", 20.1, 32.9, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R9", "1k", 20.1, 35.5, crtyd=RC)
    b.place("LED_SMD:LED_0603_1608Metric", "D1", "LED_RED", 23.4, 32.9, crtyd=RC)
    b.place("LED_SMD:LED_0603_1608Metric", "D2", "LED_GRN", 23.4, 35.5, crtyd=RC)
    b.place("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", "J2", "Conn_01x04", 4.5, 26.5,
            crtyd=(-1.52, -1.52, 1.52, 9.14))
    b.place("Resistor_SMD:R_0603_1608Metric", "R3", "5.1k", 44, 30, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R4", "5.1k", 44, 32, crtyd=RC)
    b.place(fps["SHT31-DFN8"], "U3", "SHT31", 50, 9, crtyd=(-1.5, -1.7, 1.5, 1.7))
    b.place("Capacitor_SMD:C_0603_1608Metric", "C4", "100nF", 45.8, 9, rot=180, crtyd=RC)
    b.place(fps["BH1750-WSOF6"], "U4", "BH1750", 50, 16, crtyd=(-1.75, -1.0, 1.75, 1.0))
    b.place("Capacitor_SMD:C_0603_1608Metric", "C5", "100nF", 45.8, 16, rot=180, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R1", "4.7k", 47.5, 12.5, rot=180, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R2", "4.7k", 47.5, 19.5, rot=180, crtyd=RC)
    b.place(fps["BMP280-LGA8"], "U5", "BMP280", 50, 24, rot=180,
            crtyd=(-1.4, -1.5, 1.4, 1.5))
    b.place("Capacitor_SMD:C_0603_1608Metric", "C6", "100nF", 45.8, 24, rot=180, crtyd=RC)
    b.place("Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", "J1", "Conn_01x03", 55, 12,
            crtyd=(-1.52, -1.52, 1.52, 6.6))

    # ---- net assignment (schematic plans) ----
    plans = {"U1": U1_PLAN, "X1": X1_PLAN, "U2": U2_PLAN, "U3": U3_PLAN,
             "U4": U4_PLAN, "U5": U5_PLAN, "BT1": BT_PLAN["BT1"],
             "BT2": BT_PLAN["BT2"], "J1": J_PLAN["J1"], "J2": J_PLAN["J2"]}
    plans.update(RX_PLAN)
    plans.update(CX_PLAN)
    plans.update(DX_PLAN)
    for ref, plan in plans.items():
        for pad, net in plan.items():
            if net:
                b.net_pad(ref, pad, net)
    b.collect_pads({(r, p): n for r, pl in plans.items()
                    for p, n in pl.items() if n})

    route_all(b)

    # ---- USB-C power fanout zones (0.5 mm pitch: zones, not tracks) ----
    b.pcb.zone("VBUS", (26.3, 33.0, 29.45, 36.0), layer="F.Cu")
    b.pcb.zone("VBUS", (30.55, 33.0, 33.35, 36.0), layer="F.Cu")
    b.pcb.zone("GND", (24.9, 33.0, 26.55, 37.3), layer="F.Cu")
    b.pcb.zone("GND", (29.55, 33.0, 30.45, 35.3), layer="F.Cu")
    b.pcb.zone("GND", (33.45, 33.0, 35.1, 37.3), layer="F.Cu")
    b.pcb.gnd_zone()

    # ---- silkscreen ----
    b.pcb.silk_text("sensenode-c6", 30, 2.5, size=1.6)
    b.pcb.silk_text("SDA6 SCL7 PIR4 BOOT9 LED8", 30, 39.2, size=1.0)
    b.pcb.silk_text("EN", 12, 15.5, size=1.0)
    b.pcb.silk_text("BOOT", 12, 25.5, size=1.0)
    b.pcb.silk_text("PIR", 55, 9.5, size=1.0)
    b.pcb.silk_text("3V3 TX RX GND", 9, 26.5, size=1.0)

    # ---- geometric self-check: prune offending copper, then verify ----
    probs = b.check_courtyards()
    if probs:
        for p in probs:
            print("SELF-CHECK:", p)
        raise SystemExit(f"self-check failed: {len(probs)} problem(s)")
    removed = b.prune((0.0, 0.0, W, H), [KEEPOUT])
    for kind, net, key in removed:
        print(f"PRUNE: removed {kind} net={net} @ {key}")
    probs = b.check_clearance((0.0, 0.0, W, H), [KEEPOUT])
    if probs:
        for p in probs:
            print("SELF-CHECK:", p)
        raise SystemExit(f"self-check failed: {len(probs)} problem(s)")
    unrouted = sorted({net for _k, net, _key in removed})
    os.makedirs(os.path.join(OUT, "analysis"), exist_ok=True)
    with open(os.path.join(OUT, "analysis", "pruned_routes.txt"), "w") as f:
        f.write("Copper objects removed by the self-check prune pass\n")
        f.write("(nets left fully/partially unrouted -- see README routing status)\n")
        for kind, net, key in removed:
            f.write(f"{kind} {net} {key}\n")
        f.write("affected nets: " + (", ".join(unrouted) or "none") + "\n")
    print("self-check OK; nets with removed copper:",
          ", ".join(unrouted) or "none")

    b.save(os.path.join(OUT, BOARD + ".kicad_pcb"))


def route_all(b):
    R, V, G = b.route, b.via, b.gvia

    # ================= GND (F.Cu stub + via per SMD pad; THT via pour) ======
    R("GND", [(21.25, 5.745), (19.9, 5.745)], 0.5); V("GND", 19.9, 5.745)
    R("GND", [(38.75, 5.745), (40.1, 5.745)], 0.5); V("GND", 40.1, 5.745)
    V("GND", 30, 14)                                   # U1 EPAD via-in-pad
    R("GND", [(20.05, 30.0), (18.9, 30.2)], 0.5); V("GND", 18.9, 30.2)   # U2 p2
    R("GND", [(15.225, 34.5), (14.3, 34.5)], 0.5); V("GND", 14.3, 34.5)  # C1 p2
    R("GND", [(18.225, 28), (17.4, 28)], 0.5); V("GND", 17.4, 28)        # C2 p2
    R("GND", [(16.225, 7), (15.4, 7)], 0.5); V("GND", 15.4, 7)           # C3 p2
    R("GND", [(17.775, 9.5), (18.05, 9.5)], 0.5); V("GND", 18.05, 9.5)   # C7 p2
    R("GND", [(16.55, 17.25), (17.9, 17.25)], 0.5); V("GND", 17.9, 17.25)  # BT1 p2
    R("GND", [(16.55, 21.75), (17.9, 21.75)], 0.5); V("GND", 17.9, 21.75)  # BT1 p4
    R("GND", [(16.55, 27.25), (17.9, 27.25)], 0.5); V("GND", 17.9, 27.25)  # BT2 p2
    R("GND", [(16.55, 31.75), (16.55, 33.4)], 0.5); V("GND", 16.55, 33.4)  # BT2 p4
    R("GND", [(24.175, 32.9), (24.175, 34.3)], 0.5); V("GND", 24.175, 34.3)  # D1 p2
    R("GND", [(44.775, 30), (46.6, 30.6)], 0.5); V("GND", 46.6, 30.6)    # R3 p2
    R("GND", [(44.775, 32), (46.2, 32.6)], 0.5); V("GND", 46.2, 32.6)    # R4 p2
    R("GND", [(45.025, 9), (44.7, 10.1)], 0.5); V("GND", 44.7, 10.1)     # C4 p2
    R("GND", [(45.025, 16), (44.2, 16)], 0.5); V("GND", 44.2, 16)        # C5 p2
    R("GND", [(45.025, 24), (44.2, 24)], 0.5); V("GND", 44.2, 24)        # C6 p2
    # U3: p2, p8, EP
    R("GND", [(49.25, 8.6), (48.3, 8.6)], 0.5); V("GND", 48.3, 8.6)
    R("GND", [(50.75, 10.2), (51.5, 10.7)], 0.5); V("GND", 51.5, 10.7)
    V("GND", 50, 9)
    # U4: p2+p3 bridge, stub, EP
    R("GND", [(48.57, 16.0), (48.57, 16.5)], 0.25)
    R("GND", [(48.57, 16.5), (47.7, 16.5)], 0.5); V("GND", 47.7, 16.5)
    V("GND", 50, 16)
    # U5: p7->p5 bridge, p5+p1 stubs
    R("GND", [(49.28, 23.68), (47.9, 23.68), (47.9, 24.98), (49.28, 24.98)], 0.5)
    R("GND", [(49.28, 24.98), (49.28, 25.9)], 0.5); V("GND", 49.28, 25.9)
    R("GND", [(50.72, 24.98), (50.72, 25.9)], 0.5); V("GND", 50.72, 25.9)
    # X1 GND zone via (pads 8/9 region; other pads -> shells -> pour)
    V("GND", 30.0, 34.9)

    # ================= VBUS =================================================
    # X1 pads -> F.Cu zones -> 2 vias -> B.Cu trunk
    V("VBUS", 29.1, 35.5); V("VBUS", 33.1, 35.8)
    R("VBUS", [(29.1, 35.5), (33.1, 35.5), (33.1, 35.8)], 0.5, "B.Cu")
    R("VBUS", [(33.1, 35.8), (33.1, 32.6), (16.775, 32.6)], 0.5, "B.Cu")
    # U2 VIN (p1) + EN (p3)
    R("VBUS", [(19.0, 32.6), (19.0, 29.05)], 0.5, "B.Cu")
    V("VBUS", 19.0, 29.05)
    R("VBUS", [(19.0, 29.05), (20.05, 29.05)], 0.5)
    R("VBUS", [(19.5, 32.6), (19.5, 31.0)], 0.5, "B.Cu")
    V("VBUS", 19.5, 31.0)
    R("VBUS", [(19.5, 31.0), (19.5, 30.95), (20.05, 30.95)], 0.5)
    # C1 (bulk cap)
    R("VBUS", [(16.775, 32.6), (16.775, 33.3)], 0.5, "B.Cu")
    V("VBUS", 16.775, 33.3)
    R("VBUS", [(16.775, 33.3), (16.775, 34.5)], 0.5)

    # ================= +3V3 =================================================
    R("+3V3", [(21.95, 29.525), (21.95, 28.6), (23.3, 28.6)], 0.5)   # U2 VOUT
    R("+3V3", [(21.95, 28.6), (21.95, 28.0), (19.775, 28.0)], 0.5)   # C2 p1
    R("+3V3", [(23.3, 28.6), (45.9, 28.6)], 0.5)                     # F.Cu trunk
    R("+3V3", [(45.9, 28.6), (45.9, 7.0)], 0.5)                      # right vertical
    # module VDD + C3 + R7
    R("+3V3", [(21.25, 7.015), (19.6, 7.015), (19.6, 7.0), (17.775, 7.0)], 0.5)
    R("+3V3", [(17.775, 7.0), (18.9, 7.0), (18.9, 11.5), (17.775, 11.5)], 0.5)
    # taps off the right vertical
    R("+3V3", [(45.9, 7.0), (51.6, 7.0), (51.6, 7.8), (50.75, 7.8)], 0.5)  # U3 p5
    R("+3V3", [(45.9, 9.0), (46.575, 9.0)], 0.5)                            # C4 p1
    R("+3V3", [(45.9, 11.0), (55.0, 11.0), (55.0, 12.0)], 0.5)              # J1 p1
    R("+3V3", [(45.9, 13.5), (48.275, 13.5), (48.275, 12.5)], 0.5)          # R1 p1
    R("+3V3", [(45.9, 15.5), (48.57, 15.5)], 0.5)                           # U4 p1
    R("+3V3", [(45.9, 16.0), (46.575, 16.0)], 0.5)                          # C5 p1
    R("+3V3", [(45.9, 17.2), (53.0, 17.2), (53.0, 16.0), (51.43, 16.0)], 0.5)  # U4 p5
    R("+3V3", [(45.9, 18.7), (48.275, 18.7), (48.275, 19.5)], 0.5)          # R2 p1
    R("+3V3", [(45.9, 23.02), (49.28, 23.02)], 0.5)                         # U5 p8
    R("+3V3", [(49.28, 23.02), (48.5, 23.02), (48.5, 24.32), (49.28, 24.32)], 0.5)  # U5 p6
    R("+3V3", [(45.9, 24.0), (46.575, 24.0)], 0.5)                          # C6 p1
    R("+3V3", [(45.9, 25.6), (51.6, 25.6), (51.6, 24.32), (50.72, 24.32)], 0.5)  # U5 p2
    # J2 p1 feed (via + B.Cu along y=28.0)
    V("+3V3", 23.3, 28.6)
    R("+3V3", [(23.3, 28.6), (23.3, 28.0), (5.8, 28.0), (5.8, 24.9)], 0.5, "B.Cu")
    V("+3V3", 5.8, 24.9)
    R("+3V3", [(5.8, 24.9), (4.5, 24.9), (4.5, 26.5)], 0.5)
    # R8/R9 LED pull-ups
    V("+3V3", 27.2, 28.6)
    R("+3V3", [(27.2, 28.6), (27.2, 31.9), (20.9, 31.9)], 0.5, "B.Cu")
    V("+3V3", 20.9, 31.9)
    R("+3V3", [(20.9, 31.9), (19.325, 31.9), (19.325, 32.9)], 0.5)
    R("+3V3", [(19.325, 32.9), (19.325, 35.5)], 0.5)

    # ================= signals ==============================================
    # EN: U1 p3 -> C7 p1 -> R7 p2 -> BT1 p1/p3
    R("EN", [(21.25, 8.285), (19.8, 8.285), (19.8, 8.6), (15.4, 8.6),
             (15.4, 11.5), (16.225, 11.5)])
    R("EN", [(15.4, 9.5), (16.225, 9.5)])
    R("EN", [(15.4, 11.5), (14.0, 11.5), (14.0, 17.25), (7.45, 17.25),
             (7.45, 21.75)])
    # BOOT: U1 p15 -> BT2 p1/p3
    R("BOOT", [(38.75, 22.255), (41.4, 22.255)])
    V("BOOT", 41.4, 22.255)
    R("BOOT", [(41.4, 22.255), (41.4, 26.9), (6.5, 26.9)], 0.25, "B.Cu")
    V("BOOT", 6.5, 26.9)
    R("BOOT", [(6.5, 26.9), (7.45, 27.25)])
    R("BOOT", [(7.45, 27.25), (7.45, 31.75)])
    # PIR_OUT: U1 p4 -> J1 p2
    R("PIR_OUT", [(21.25, 9.555), (20.0, 9.555)])
    V("PIR_OUT", 20.0, 9.555)
    R("PIR_OUT", [(20.0, 9.555), (20.0, 9.9), (56.2, 9.9), (56.2, 14.54),
                  (55.0, 14.54)], 0.25, "B.Cu")
    # STAT_LED: U1 p10 -> D2 cathode
    R("STAT_LED", [(21.25, 17.175), (19.8, 17.175), (19.8, 18.6),
                   (13.4, 18.6), (13.4, 36.8), (24.175, 36.8), (24.175, 35.5)])
    # LED anode nets
    R("LED1_A", [(20.875, 32.9), (22.625, 32.9)])
    R("LED2_A", [(20.875, 35.5), (22.625, 35.5)])
    # USB module side
    R("USB_DM", [(21.25, 20.985), (20.3, 20.985), (20.3, 23.5), (20.375, 23.5)])
    R("USB_DP", [(21.25, 22.255), (21.0, 22.255), (21.0, 26.2), (20.375, 26.2)])
    # USB connector side (X1 pads -> vias -> B.Cu -> left edge -> R6/R5)
    R("USB_DM_CON", [(28.25, 34), (28.1, 35.5)])
    V("USB_DM_CON", 28.1, 35.5)
    R("USB_DM_CON", [(31.75, 34), (31.4, 36.6)])
    V("USB_DM_CON", 31.4, 36.6)
    R("USB_DM_CON", [(28.1, 35.5), (28.1, 36.9), (31.4, 36.9), (31.4, 36.6)],
      0.25, "B.Cu")
    R("USB_DM_CON", [(28.1, 36.9), (5.6, 36.9), (5.6, 38.6), (1.5, 38.6),
                     (1.5, 22.0)], 0.25, "B.Cu")
    V("USB_DM_CON", 1.5, 22.0)
    R("USB_DM_CON", [(1.5, 22.0), (1.5, 23.5), (18.825, 23.5)])
    R("USB_DP_CON", [(27.75, 34), (27.5, 37.8)])
    V("USB_DP_CON", 27.5, 37.8)
    R("USB_DP_CON", [(32.25, 34), (32.25, 36.3)])
    V("USB_DP_CON", 32.25, 36.3)
    R("USB_DP_CON", [(27.5, 37.8), (32.25, 37.8), (32.25, 36.3)], 0.25, "B.Cu")
    R("USB_DP_CON", [(27.5, 37.8), (6.3, 37.8), (6.3, 39.2), (0.8, 39.2),
                     (0.8, 24.8)], 0.25, "B.Cu")
    V("USB_DP_CON", 0.8, 24.8)
    R("USB_DP_CON", [(0.8, 24.8), (3.0, 24.8), (3.0, 24.0), (16.9, 24.0),
                     (16.9, 26.2), (18.825, 26.2)])
    # CC pull-downs: stubs up into board, B.Cu lanes to R3/R4
    R("USB_CC1", [(32.75, 34), (32.75, 31.6)])
    V("USB_CC1", 32.75, 31.6)
    R("USB_CC1", [(32.75, 31.6), (45.6, 31.6), (45.6, 29.2)], 0.25, "B.Cu")
    V("USB_CC1", 45.6, 29.2)
    R("USB_CC1", [(45.6, 29.2), (42.0, 29.2), (42.0, 30.0), (43.225, 30.0)])
    R("USB_CC2", [(27.25, 34), (27.25, 31.6)])
    V("USB_CC2", 27.25, 31.6)
    R("USB_CC2", [(27.25, 30.8), (44.0, 30.8), (44.0, 31.2)],
      0.25, "B.Cu")
    V("USB_CC2", 44.0, 31.2)
    R("USB_CC2", [(44.0, 31.2), (44.0, 32.0), (43.225, 32.0)])
    # UART: TX0 -> J2 p2, RX0 -> J2 p3 (B.Cu)
    R("TX0", [(38.75, 9.555), (39.9, 9.555)])
    V("TX0", 39.9, 9.555)
    R("TX0", [(39.9, 9.555), (39.9, 25.6), (2.6, 25.6), (2.6, 29.04),
              (4.5, 29.04)], 0.25, "B.Cu")
    R("RX0", [(38.75, 10.825), (40.6, 10.825)])
    V("RX0", 40.6, 10.825)
    R("RX0", [(40.6, 10.825), (40.6, 26.2), (3.2, 26.2), (3.2, 31.58),
              (4.5, 31.58)], 0.25, "B.Cu")
    # I2C SDA: U1 p6 -> B.Cu trunk y=12.095
    R("I2C_SDA", [(21.25, 12.095), (19.9, 12.095)])
    V("I2C_SDA", 19.9, 12.095)
    R("I2C_SDA", [(19.9, 12.095), (53.7, 12.095)], 0.25, "B.Cu")
    # SDA branches: U3 p1, R1 p2, U5 p3, U4 p4
    V("I2C_SDA", 44.0, 12.095)
    R("I2C_SDA", [(44.0, 12.095), (44.0, 7.8), (49.25, 7.8)])
    V("I2C_SDA", 46.725, 12.095)
    R("I2C_SDA", [(46.725, 12.095), (46.725, 12.5)])
    R("I2C_SDA", [(53.7, 12.095), (53.7, 23.68)], 0.25, "B.Cu")
    V("I2C_SDA", 53.7, 23.68)
    R("I2C_SDA", [(53.7, 23.68), (50.72, 23.68)])
    R("I2C_SDA", [(53.2, 12.095), (53.2, 18.2)], 0.25, "B.Cu")
    V("I2C_SDA", 53.2, 18.2)
    R("I2C_SDA", [(53.2, 18.2), (51.43, 18.2), (51.43, 16.5)])
    # I2C SCL: U1 p7 -> B.Cu trunk y=13.365
    R("I2C_SCL", [(21.25, 13.365), (19.9, 13.365)])
    V("I2C_SCL", 19.9, 13.365)
    R("I2C_SCL", [(19.9, 13.365), (52.5, 13.365)], 0.25, "B.Cu")
    # SCL branches: U3 p4, R2 p2, U4 p6, U5 p4
    R("I2C_SCL", [(46.0, 13.365), (46.0, 10.2)], 0.25, "B.Cu")
    V("I2C_SCL", 46.0, 10.2)
    R("I2C_SCL", [(46.0, 10.2), (49.25, 10.2)])
    R("I2C_SCL", [(46.725, 13.365), (46.725, 20.6)], 0.25, "B.Cu")
    V("I2C_SCL", 46.725, 20.6)
    R("I2C_SCL", [(46.725, 20.6), (46.725, 19.5)])
    R("I2C_SCL", [(51.43, 13.365), (51.43, 14.0)], 0.25, "B.Cu")
    V("I2C_SCL", 51.43, 14.0)
    R("I2C_SCL", [(51.43, 14.0), (51.43, 15.5)])
    R("I2C_SCL", [(52.5, 13.365), (52.5, 22.0)], 0.25, "B.Cu")
    V("I2C_SCL", 52.5, 22.0)
    R("I2C_SCL", [(52.5, 22.0), (52.5, 23.02), (50.72, 23.02)])


# --------------------------------------------------------------------------
# BOM + main
# --------------------------------------------------------------------------
def write_bom(path):
    rows = [("U1", "ESP32-C6-WROOM-1"), ("X1", "USB_C_16P"),
            ("U2", "AP2112K-3.3"), ("U3", "SHT31"), ("U4", "BH1750"),
            ("U5", "BMP280"), ("R1", "4.7k"), ("R2", "4.7k"), ("R3", "5.1k"),
            ("R4", "5.1k"), ("R5", "22R"), ("R6", "22R"), ("R7", "10k"),
            ("R8", "1k"), ("R9", "1k"), ("C1", "10uF"), ("C2", "10uF"),
            ("C3", "100nF"), ("C4", "100nF"), ("C5", "100nF"), ("C6", "100nF"),
            ("C7", "100nF"), ("D1", "LED_RED"), ("D2", "LED_GRN"),
            ("BT1", "SW_PUSH"), ("BT2", "SW_PUSH"), ("J1", "Conn_01x03"),
            ("J2", "Conn_01x04")]
    with open(path, "w") as f:
        f.write("Ref,Value,Footprint,LCSC,MPN,Qty\n")
        for ref, val in rows:
            fp, _desc, lcsc, mpn = PART_INFO[val]
            f.write(f"{ref},{val},{fp},{lcsc},{mpn},1\n")


def main():
    kg.write_project(os.path.join(OUT, BOARD + ".kicad_pro"), BOARD, BOARD + "-lib")
    fps = build_footprints(BOARD)
    build_schematic(os.path.join(OUT, BOARD + ".kicad_sch"))
    build_pcb(fps)
    write_bom(os.path.join(OUT, "bom_lcsc.csv"))
    problems = kg.validate_project(OUT)
    for p in problems:
        print("VALIDATE:", p)
    if problems:
        raise SystemExit(f"validate_project failed: {len(problems)} problem(s)")
    print("sensenode-c6: project generated + validated")


if __name__ == "__main__":
    main()
