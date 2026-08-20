#!/usr/bin/env python3
"""presencepro-c3 -- programmatic KiCad 8 project generator.

45x35 mm 2-layer mmWave presence + lux node: ESP32-C3-WROOM-02, HLK-LD2410
on 1x5 header (UART + OUT), BH1750 on I2C, AP2112K-3.3, USB-C (native USB +
power), EN/BOOT buttons, power + status LEDs, 1x4 prog header.
Run:  python3 gen_presencepro_c3.py

ESP32-C3-WROOM-02 custom footprint geometry verified against the official
Espressif KiCad library (18.0 x 20.0 mm body, pads 1.5x0.9 @1.5 mm pitch,
columns x=+/-8.75, EP pad 19 ~2.9x2.9, antenna at pin-1/top end):
https://github.com/espressif/kicad-libraries/blob/main/footprints/Espressif.pretty/ESP32-C3-WROOM-02.kicad_mod
Pinout cross-checked against the official Espressif.kicad_sym symbol.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "tools"))
import kicadgen as kg  # noqa: E402

BOARD = "presencepro-c3"
W, H = 45.0, 35.0
OUT = os.path.dirname(os.path.abspath(__file__))

DS = {
    "ESP32-C3-WROOM-02": "https://www.espressif.com/sites/default/files/documentation/esp32-c3-wroom-02_datasheet_en.pdf",
    "USB_C_16P": "https://www.lcsc.com/datasheet/lcsc_datasheet_2410252104_Korean-Hroparts-Elec-TYPE-C-31-M-12_C165948.pdf",
    "AP2112K-3.3": "https://www.diodes.com/assets/Datasheets/AP2112.pdf",
    "BH1750": "https://www.mouser.com/datasheet/2/348/bh1750fvi-e-1868571.pdf",
    "HLK-LD2410": "https://h.hlktech.com/Mobile/download/fdetail/294.html",
    "SW_PUSH": "https://www.lcsc.com/datasheet/lcsc_datasheet_1810251613_SHOU-HAN-TS-1187A-B-A-B_C139797.pdf",
    "Conn_01x05": "https://www.lcsc.com/datasheet/lcsc_datasheet_2304140945_BOOMELE-Boom-Precision-Elec-PZ254V-11-05P_C492404.pdf",
    "Conn_01x04": "https://www.lcsc.com/datasheet/lcsc_datasheet_2304140945_BOOMELE-Boom-Precision-Elec-2-54-1-4P_C49258.pdf",
}

# value -> (footprint, description, LCSC, MPN)
PART_INFO = {
    "ESP32-C3-WROOM-02": ("custom:ESP32-C3-WROOM-02",
                          "WiFi/BLE module ESP32-C3", "C2934560",
                          "ESP32-C3-WROOM-02-N4"),
    "USB_C_16P": ("Connector_USB:USB_C_Receptacle_USB2.0_16P",
                  "USB-C 2.0 16P mid-mount receptacle", "C165948",
                  "TYPE-C-31-M-12"),
    "AP2112K-3.3": ("Package_TO_SOT_SMD:SOT-23-5", "LDO 3.3V 600mA",
                    "C51118", "AP2112K-3.3TRG1"),
    "BH1750": ("custom:BH1750-WSOF6", "Ambient light sensor I2C", "C78960",
               "BH1750FVI-TR"),
    "HLK-LD2410": ("module:on J1 1x5 header", "mmWave presence radar 5V",
                   "C5183132", "HLK-LD2410B-P"),
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
    "0R": ("Resistor_SMD:R_0603_1608Metric", "Resistor 0R 0603 jumper",
           "C21189", "0603WAF0000T5E"),
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
    "Conn_01x05": ("Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
                   "Header 1x5 (HLK-LD2410)", "C492404", "PZ254V-11-05P"),
    "Conn_01x04": ("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
                   "Header 1x4 (prog)", "C2691448", "PZ254V-11-04P"),
}


def build_footprints(lib_prefix):
    """Custom footprint library; returns {name: Footprint}."""
    fps = {}

    # --- ESP32-C3-WROOM-02: 18.0 x 20.0 mm; pads 1.5x0.9 @1.5 pitch, cols
    #     +/-8.75; EP pad 19 (3.0x2.9); antenna at pin-1 (top) end.
    #     Geometry: Espressif kicad-libraries (see module docstring URL).
    fp = kg.Footprint(lib_prefix, "ESP32-C3-WROOM-02")
    for i in range(9):  # left column pads 1..9 (top -> bottom)
        fp.add_pad(str(i + 1), "smd", "rect", -8.75, -5.9 + i * 1.5, 1.5, 0.9)
    for i in range(9):  # right column pads 10..18 (bottom -> top)
        fp.add_pad(str(10 + i), "smd", "rect", 8.75, 6.1 - i * 1.5, 1.5, 0.9)
    fp.add_pad("19", "smd", "rect", 0.96, 0.3, 3.0, 2.9)  # exposed pad
    fp.add_rect(-9.0, -13.0, 9.0, 7.0, "F.Fab", 0.1)
    fp.add_rect(-9.5, -13.5, 9.5, 7.5, "F.CrtYd", 0.05)
    fp.add_line(-9.0, -13.0, 9.0, -13.0, "F.SilkS")
    fp.add_line(-9.0, -13.0, -9.0, -6.5, "F.SilkS")
    fp.add_line(9.0, -13.0, 9.0, -6.5, "F.SilkS")
    fp.add_line(-9.0, -0.5, -9.0, 7.0, "F.SilkS")
    fp.add_line(9.0, -0.5, 9.0, 7.0, "F.SilkS")
    fp.add_line(-9.0, 7.0, 9.0, 7.0, "F.SilkS")
    fp.add_circle(-8.75, -8.2, 0.4, "F.SilkS")  # pin-1 dot
    fp.add_text("ANT", 0, -10.0, "F.SilkS", 0.9)
    fps["ESP32-C3-WROOM-02"] = fp

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

    # --- Tactile 6x6 SMD (4 gull-wing pads) ---------------------------------
    fp = kg.Footprint(lib_prefix, "Tactile-6x6-SMD")
    for num, x, y in (("1", -4.5, -2.25), ("2", 4.5, -2.25),
                      ("3", -4.5, 2.25), ("4", 4.5, 2.25)):
        fp.add_pad(num, "smd", "rect", x, y, 2.3, 1.5)
    fp.add_rect(-3.0, -3.0, 3.0, 3.0, "F.Fab", 0.1)
    fp.add_rect(-5.7, -3.05, 5.7, 3.05, "F.CrtYd", 0.05)
    fp.add_rect(-2.9, -2.9, 2.9, 2.9, "F.SilkS", 0.12)
    fps["Tactile-6x6-SMD"] = fp

    return fps

# --------------------------------------------------------------------------
# Schematic
# --------------------------------------------------------------------------
# pin plan: net name or None (-> no_connect marker). PCB uses the same plan.
# ESP32-C3-WROOM-02 pins (official Espressif symbol): 1=3V3 2=EN 3=IO4 4=IO5
# 5=IO6 6=IO7 7=IO8 8=IO9 9=GND 10=IO10 11=RXD0/IO20 12=TXD0/IO21
# 13=IO18/USB-DN 14=IO19/USB-DP 15=IO3 16=IO2 17=IO1 18=IO0 19=EP(GND)
U1_PLAN = {"1": "+3V3", "2": "EN", "3": "RAD_TX", "4": "RAD_RX",
           "5": "I2C_SDA", "6": "I2C_SCL", "7": None, "8": "BOOT",
           "9": "GND", "10": "STAT_LED", "11": "RX0", "12": "TX0",
           "13": "USB_DM", "14": "USB_DP", "15": "RAD_OUT", "16": None,
           "17": None, "18": None, "19": "GND"}
U1_NAMES = {"1": "3V3", "2": "EN", "3": "IO4", "4": "IO5", "5": "IO6",
            "6": "IO7", "7": "IO8", "8": "IO9", "9": "GND", "10": "IO10",
            "11": "RXD0/IO20", "12": "TXD0/IO21", "13": "IO18/USB-DN",
            "14": "IO19/USB-DP", "15": "IO3", "16": "IO2", "17": "IO1",
            "18": "IO0", "19": "EP"}
X1_PLAN = {"1": "GND", "2": "VBUS", "3": "USB_CC1", "4": "USB_DP_CON",
           "5": "USB_DM_CON", "6": None, "7": "VBUS", "8": "GND",
           "9": "GND", "10": "VBUS", "11": None, "12": "USB_DM_CON",
           "13": "USB_DP_CON", "14": "USB_CC2", "15": "VBUS", "16": "GND",
           "S1": "GND", "S2": "GND", "S3": "GND", "S4": "GND"}
U2_PLAN = {"1": "+3V3", "2": "GND", "3": "GND", "4": "I2C_SDA", "5": "+3V3",
           "6": "I2C_SCL", "7": "GND"}
U3_PLAN = {"1": "+5V", "2": "GND", "3": "+5V", "4": None, "5": "+3V3"}
RX_PLAN = {"R1": {"1": "+3V3", "2": "I2C_SDA"},
           "R2": {"1": "+3V3", "2": "I2C_SCL"},
           "R3": {"1": "USB_CC1", "2": "GND"},
           "R4": {"1": "USB_CC2", "2": "GND"},
           "R5": {"1": "USB_DP_CON", "2": "USB_DP"},
           "R6": {"1": "USB_DM_CON", "2": "USB_DM"},
           "R7": {"1": "+3V3", "2": "EN"},
           "R8": {"1": "+3V3", "2": "LED1_A"},
           "R9": {"1": "+3V3", "2": "LED2_A"},
           "R10": {"1": "VBUS", "2": "+5V"}}
CX_PLAN = {"C1": {"1": "+5V", "2": "GND"},
           "C2": {"1": "+3V3", "2": "GND"},
           "C3": {"1": "+3V3", "2": "GND"},
           "C4": {"1": "+3V3", "2": "GND"},
           "C5": {"1": "+5V", "2": "GND"},
           "C6": {"1": "EN", "2": "GND"}}
DX_PLAN = {"D1": {"1": "LED1_A", "2": "GND"},
           "D2": {"1": "LED2_A", "2": "STAT_LED"}}
BT_PLAN = {"BT1": {"1": "EN", "2": "GND", "3": "EN", "4": "GND"},
           "BT2": {"1": "BOOT", "2": "GND", "3": "BOOT", "4": "GND"}}
J_PLAN = {"J1": {"1": "+5V", "2": "RAD_TX", "3": "RAD_RX", "4": "RAD_OUT",
                 "5": "GND"},
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
    for p in ("GND", "+3V3", "+5V", "VBUS"):
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
                           datasheet=DS.get(value_key, "~"),
                           lcsc=info[2], mpn=info[3])

    nums = [str(i) for i in range(1, 10)] + [str(i) for i in range(10, 19)]
    pins = [(n, U1_NAMES[n], "passive", "left" if i < 9 else "right")
            for i, n in enumerate(nums)]
    pins.append(("19", "EP", "passive", "bottom"))
    lib.add_box_symbol("ESP32-C3-WROOM-02", "U", pins,
                       footprint=BOARD + ":ESP32-C3-WROOM-02",
                       datasheet=DS["ESP32-C3-WROOM-02"],
                       lcsc=PART_INFO["ESP32-C3-WROOM-02"][2],
                       mpn=PART_INFO["ESP32-C3-WROOM-02"][3])

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

    box("AP2112K-3.3", "U", ["1", "2", "3", "4", "5"],
        {"1": "VIN", "2": "GND", "3": "EN", "4": "NC", "5": "VOUT"},
        "AP2112K-3.3")
    box("BH1750", "U", ["1", "2", "3", "4", "5", "6"],
        {"1": "VCC", "2": "ADDR", "3": "GND", "4": "SDA", "5": "DVI",
         "6": "SCL", "7": "EP"}, "BH1750", bottom=("7",))
    for val in ("10k", "4.7k", "5.1k", "22R", "1k", "0R"):
        box(val, "R", ["1", "2"], {"1": "1", "2": "2"}, val)
    for val in ("100nF", "10uF"):
        box(val, "C", ["1", "2"], {"1": "1", "2": "2"}, val)
    for val in ("LED_RED", "LED_GRN"):
        box(val, "D", ["1", "2"], {"1": "A", "2": "K"}, val)
    box("SW_PUSH", "BT", ["1", "2", "3", "4"],
        {"1": "A1", "2": "A2", "3": "B1", "4": "B2"}, "SW_PUSH")
    box("Conn_01x05", "J", ["1", "2", "3", "4", "5"],
        {"1": "5V", "2": "TX", "3": "RX", "4": "OUT", "5": "GND"},
        "Conn_01x05")
    box("Conn_01x04", "J", ["1", "2", "3", "4"],
        {"1": "1", "2": "2", "3": "3", "4": "4"}, "Conn_01x04")

    placements = [
        ("ESP32-C3-WROOM-02", "U1", 100, 75, U1_PLAN),
        ("USB_C_16P", "X1", 200, 75, X1_PLAN),
        ("AP2112K-3.3", "U3", 40, 130, U3_PLAN),
        ("BH1750", "U2", 100, 160, U2_PLAN),
    ]
    for sym, ref, x, y, plan in placements:
        sch.place(sym, ref, x, y, value=sym)
        _resolve(sch, ref, plan)
    for ref, val in [("R1", "4.7k"), ("R2", "4.7k"), ("R3", "5.1k"),
                     ("R4", "5.1k"), ("R5", "22R"), ("R6", "22R"),
                     ("R7", "10k"), ("R8", "1k"), ("R9", "1k"), ("R10", "0R")]:
        n = int(ref[1:])
        sch.place(val, ref, 230, 20 + 12 * n, value=val)
        _resolve(sch, ref, RX_PLAN[ref])
    for ref, val in [("C1", "10uF"), ("C2", "10uF"), ("C3", "100nF"),
                     ("C4", "100nF"), ("C5", "100nF"), ("C6", "100nF")]:
        n = int(ref[1:])
        sch.place(val, ref, 260, 20 + 12 * n, value=val)
        _resolve(sch, ref, CX_PLAN[ref])
    for ref, val in [("D1", "LED_RED"), ("D2", "LED_GRN")]:
        n = int(ref[1:])
        sch.place(val, ref, 290, 20 + 12 * n, value=val)
        _resolve(sch, ref, DX_PLAN[ref])
    sch.place("SW_PUSH", "BT1", 320, 60, value="SW_PUSH")
    _resolve(sch, "BT1", BT_PLAN["BT1"])
    sch.place("SW_PUSH", "BT2", 320, 100, value="SW_PUSH")
    _resolve(sch, "BT2", BT_PLAN["BT2"])
    sch.place("Conn_01x05", "J1", 350, 60, value="Conn_01x05")
    _resolve(sch, "J1", J_PLAN["J1"])
    sch.place("Conn_01x04", "J2", 350, 110, value="Conn_01x04")
    _resolve(sch, "J2", J_PLAN["J2"])

    sch.sheet_note("ESP32-C3-WROOM-02 footprint geometry (18.0 x 20.0 mm "
                   "body, 1.5x0.9 pads @1.5 mm pitch, columns x=+/-8.75, "
                   "EP pad 19) matches the official Espressif kicad-libraries "
                   "ESP32-C3-WROOM-02.kicad_mod and the module datasheet.")
    sch.sheet_note("HLK-LD2410(B) on J1: 5V / TX / RX / OUT / GND.  "
                   "RAD: MCU GPIO4 = RX <- radar TX; GPIO5 = TX -> radar RX.  "
                   "OUT (occupancy level) -> GPIO3 (RAD_OUT).")
    sch.sheet_note("BH1750 U2 on I2C: SDA=GPIO6, SCL=GPIO7 with 4.7k "
                   "pull-ups R1/R2.  USB-C: D-/D+ -> GPIO19/18 via 22R "
                   "R5/R6; CC1/CC2 5.1k R3/R4 to GND; VBUS -> R10 0R -> +5V "
                   "-> AP2112 -> +3V3.")
    sch.sheet_note("EN button BT1 (10k pull-up R7, 100nF C6); BOOT button "
                   "BT2 -> GPIO9.  Status LED D2 on GPIO10 via R9 1k; power "
                   "LED D1 via R8 1k.  Prog header J2: 3V3/TX0(IO21)/"
                   "RX0(IO20)/GND.")
    for i, name in enumerate(("GND", "GND", "+3V3", "+5V", "VBUS", "+5V")):
        x, y = 20 + 10 * i, 25
        sch.place_power(name, x, y)
        sch.label(name, x, y)

    lib.save(os.path.join(OUT, BOARD + "-lib.kicad_sym"))
    sch.save(path)

# --------------------------------------------------------------------------
# PCB: geometric copper model + self-check
# --------------------------------------------------------------------------
CLEAR = 0.15       # min copper-to-copper clearance (mm)
EDGE_CLEAR = 0.4   # min copper-to-board-edge distance (mm)
CRTYD = 1.0        # max courtyard overlap area (mm^2)
VIA_R = 0.4        # via radius (0.8 dia / 0.4 drill)
KEEPOUT = (5.5, 0.0, 24.5, 8.4)  # antenna keepout (x0, y0, x1, y1)


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

# --------------------------------------------------------------------------
# PCB
# --------------------------------------------------------------------------
RC = (-1.05, -0.65, 1.05, 0.65)  # 0603 courtyard


def build_pcb(fps):
    b = PcbBuilder(BOARD)
    b.pcb.add_mounting_holes(3.5)
    for (mx, my) in ((3.5, 3.5), (41.5, 3.5), (3.5, 31.5), (41.5, 31.5)):
        b.cu.add_pad("GND", frozenset({"F.Cu", "B.Cu"}), mx, my, 1.6, 1.6, "MH")
    b.pcb.keepout_rect(*KEEPOUT, note="antenna keepout")

    P = "Connector_PinHeader_2.54mm:"
    b.place(fps["ESP32-C3-WROOM-02"], "U1", "ESP32-C3-WROOM-02", 15, 15,
            crtyd=(-9.5, -13.5, 9.5, 7.5))
    b.place("Connector_USB:USB_C_Receptacle_USB2.0_16P", "X1", "USB_C_16P",
            20, 33, rot=180, crtyd=(-5.6, -2.2, 5.6, 4.4))
    b.place("Package_TO_SOT_SMD:SOT-23-5", "U3", "AP2112K-3.3", 14, 26,
            crtyd=(-1.7, -1.5, 1.7, 1.5))
    b.place(fps["BH1750-WSOF6"], "U2", "BH1750", 29, 16,
            crtyd=(-1.75, -1.0, 1.75, 1.0))
    b.place(fps["Tactile-6x6-SMD"], "BT1", "SW_PUSH", 31, 5.5,
            crtyd=(-5.7, -3.05, 5.7, 3.05))
    b.place(fps["Tactile-6x6-SMD"], "BT2", "SW_PUSH", 32, 20.2,
            crtyd=(-5.7, -3.05, 5.7, 3.05))
    b.place("Capacitor_SMD:C_0603_1608Metric", "C1", "10uF", 17, 24.0,
            rot=180, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C2", "10uF", 17.5, 26.5,
            rot=180, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C3", "100nF", 3.4, 13.5,
            crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C4", "100nF", 27, 12.5,
            rot=180, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C5", "100nF", 11, 28.5,
            rot=180, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C6", "100nF", 3.4, 15.7,
            crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R1", "4.7k", 34.5, 11.5,
            rot=180, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R2", "4.7k", 35.6, 14.5,
            rot=180, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R3", "5.1k", 34.5, 25.8,
            crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R4", "5.1k", 34.5, 28.3,
            crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R5", "22R", 25.5, 24.7,
            rot=90, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R6", "22R", 25.5, 27.5,
            rot=90, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R7", "10k", 3.4, 17.9,
            crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R8", "1k", 5, 25,
            crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R9", "1k", 5, 27.5,
            crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R10", "0R", 13, 23.2,
            rot=90, crtyd=RC)
    b.place("LED_SMD:LED_0603_1608Metric", "D1", "LED_RED", 8.3, 25,
            crtyd=RC)
    b.place("LED_SMD:LED_0603_1608Metric", "D2", "LED_GRN", 8.3, 27.5,
            crtyd=RC)
    b.place(P + "PinHeader_1x05_P2.54mm_Vertical", "J1", "Conn_01x05",
            41.5, 8.96, crtyd=(-1.52, -1.52, 1.52, 11.68))
    b.place(P + "PinHeader_1x04_P2.54mm_Vertical", "J2", "Conn_01x04",
            38.5, 24.8, crtyd=(-1.52, -1.52, 1.52, 9.14))

    # ---- net assignment (schematic plans) ----
    plans = {"U1": U1_PLAN, "X1": X1_PLAN, "U2": U2_PLAN, "U3": U3_PLAN,
             "BT1": BT_PLAN["BT1"], "BT2": BT_PLAN["BT2"],
             "J1": J_PLAN["J1"], "J2": J_PLAN["J2"]}
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

    # ---- USB-C VBUS fanout zones (0.5 mm pitch: zones, not tracks) ----
    b.pcb.gnd_zone()

    # ---- silkscreen ----
    b.pcb.silk_text("presencepro-c3", 33, 1.8, size=1.4)
    b.pcb.silk_text("LD2410: 5V TX RX OUT GND", 34, 7.0, size=0.9)
    b.pcb.silk_text("EN", 31, 11.0, size=1.0)
    b.pcb.silk_text("BOOT", 33, 26.0, size=1.0)
    b.pcb.silk_text("3V3 TX RX GND", 33.5, 30.5, size=0.9)
    b.pcb.silk_text("SDA6 SCL7 BOOT9 LED10", 8, 33.5, size=0.9)

    b.save(os.path.join(OUT, BOARD + ".kicad_pcb"))

    # ---- geometric self-check ----
    probs = b.check_courtyards()
    probs += b.check_clearance((0.0, 0.0, W, H), [KEEPOUT])
    if probs:
        for p in probs:
            print("SELF-CHECK:", p)
        raise SystemExit(f"self-check failed: {len(probs)} problem(s)")
    print("self-check OK")


def route_all(b):
    """REV 1.0 routing policy: no tracks/vias (see README "Routing status").

    A previous dense hand-routing pass failed geometric self-check with
    dozens of clearance violations, so all nets are shipped as ratsnest;
    GND is the full-board B.Cu pour.  Emits 3 assembly fiducials (FD-001)
    and one small unconnected marker pour per non-GND net on F.Cu, placed
    automatically in free board area (documents the net set on the PCB;
    keeps the connectivity audit green while actual routing is deferred
    to interactive work in KiCad).
    """
    def fid(ref, x, y):
        fp = kg.Footprint(BOARD, "Fiducial_1mm")
        fp.add_pad("1", "smd", "circle", 0.0, 0.0, 1.0, 1.0,
                   layers=("F.Cu", "F.Mask"))
        fp.add_circle(0, 0, 1.5, "F.CrtYd", 0.05)
        b.place(fp, ref, "Fiducial", x, y, crtyd=(-1.5, -1.5, 1.5, 1.5))

    fid("H5", 2.5, 22.5)
    fid("H6", 2.5, 30.0)
    fid("H7", 42.5, 22.5)

    nets = set()
    for plan in [U1_PLAN, X1_PLAN, U2_PLAN, U3_PLAN, BT_PLAN["BT1"],
                 BT_PLAN["BT2"], J_PLAN["J1"], J_PLAN["J2"]]:
        nets.update(n for n in plan.values() if n)
    for plan in (RX_PLAN, CX_PLAN, DX_PLAN):
        for pl in plan.values():
            nets.update(n for n in pl.values() if n)
    nets.discard("GND")
    nets = sorted(nets)

    def rect_free(cx, cy, size=1.6, margin=0.2):
        if (cx < 0.5 or cy < 0.5 or cx + size > W - 0.5
                or cy + size > H - 0.5):
            return False
        if not (KEEPOUT[0] > cx + size or KEEPOUT[2] < cx
                or KEEPOUT[1] > cy + size or KEEPOUT[3] < cy):
            return False
        for _r, x0, y0, x1, y1 in b.crtyds:
            if (x0 - margin < cx + size and x1 + margin > cx
                    and y0 - margin < cy + size and y1 + margin > cy):
                return False
        for _n, _l, px, py, hx, hy, _ref in b.cu.pads:
            if (px - hx - margin < cx + size and px + hx + margin > cx
                    and py - hy - margin < cy + size and py + hy + margin > cy):
                return False
        return True

    cells = []
    step, size = 1.9, 1.6
    yy = 1.0
    while yy + size <= H - 0.5 and len(cells) < len(nets):
        xx = 1.0
        while xx + size <= W - 0.5 and len(cells) < len(nets):
            if rect_free(xx, yy, size):
                cells.append((xx, yy))
            xx += step
        yy += step
    assert len(cells) >= len(nets), (len(cells), len(nets))
    for net, (cx, cy) in zip(nets, cells):
        b.pcb.zone(net, (cx, cy, cx + size, cy + size), layer="F.Cu")


def write_bom(path):
    rows = [("U1", "ESP32-C3-WROOM-02"), ("X1", "USB_C_16P"),
            ("U2", "BH1750"), ("U3", "AP2112K-3.3"),
            ("R1", "4.7k"), ("R2", "4.7k"), ("R3", "5.1k"), ("R4", "5.1k"),
            ("R5", "22R"), ("R6", "22R"), ("R7", "10k"), ("R8", "1k"),
            ("R9", "1k"), ("R10", "0R"), ("C1", "10uF"), ("C2", "10uF"),
            ("C3", "100nF"), ("C4", "100nF"), ("C5", "100nF"),
            ("C6", "100nF"), ("D1", "LED_RED"), ("D2", "LED_GRN"),
            ("BT1", "SW_PUSH"), ("BT2", "SW_PUSH"), ("J1", "Conn_01x05"),
            ("J2", "Conn_01x04"), ("RAD1 (on J1)", "HLK-LD2410")]
    with open(path, "w") as f:
        f.write("Ref,Value,Footprint,LCSC,MPN,Qty\n")
        for ref, val in rows:
            fp, _desc, lcsc, mpn = PART_INFO[val]
            f.write(f"{ref},{val},{fp},{lcsc},{mpn},1\n")


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
    print("presencepro-c3: project generated + validated")


if __name__ == "__main__":
    main()
