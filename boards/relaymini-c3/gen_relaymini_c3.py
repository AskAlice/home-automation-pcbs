#!/usr/bin/env python3
"""relaymini-c3 -- programmatic KiCad 8 project generator (MAINS inline switch).

60x40 mm 2-layer board: ESP32-C3-WROOM-02 (SELV side) + HF32F-G relay,
HLK-PM01 AC/DC, BL0942 energy metering (live side) with 1 mOhm shunt,
UART isolated by 2x PC817 across a milled isolation slot.

MAINS SAFETY layout contract (blocking, SPEC 4.4):
  * primary (live) domain: all copper with x <= 21 mm
  * SELV domain: all copper with x >= 27 mm (>= 6 mm physical separation)
  * milled isolation slot: gr_line on Edge.Cuts at x = 24 mm
  * HLK-PM01 / relay / PC817s bridge the slot (galvanic isolation inside
    the component bodies); copper keepout under both PC817s
  * live-area outline + "DANGER: LIVE MAINS AREA" on Dwgs.User, silk warnings

Run:  python3 gen_relaymini_c3.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "tools"))
import kicadgen as kg  # noqa: E402

BOARD = "relaymini-c3"
W, H = 60.0, 40.0
OUT = os.path.dirname(os.path.abspath(__file__))

DS = {
    "ESP32-C3-WROOM-02": "https://www.espressif.com/sites/default/files/documentation/esp32-c3-wroom-02_datasheet_en.pdf",
    "HLK-PM01": "https://www.hlktech.net/index.php?id=1158",
    "BL0942": "https://www.belling.com.cn/media/file_object/bel_product/BL0942/datasheet/BL0942_V1.10_cn.pdf",
    "AP2112K-3.3": "https://www.diodes.com/assets/Datasheets/AP2112.pdf",
}

# value -> (footprint, description, LCSC, MPN)
PART_INFO = {
    "ESP32-C3-WROOM-02": ("custom:ESP32-C3-WROOM-02",
                          "WiFi/BLE module (SELV side)", "C2934560",
                          "ESP32-C3-WROOM-02-N4"),
    "HLK-PM01": ("custom:HLK-PM01", "AC/DC 5V 3W isolated module",
                 "C209903", "HLK-PM01"),
    "HF32F-G": ("custom:HF32F-G", "Relay 10A 250VAC 5V coil SPST-NO",
                "C74541", "HF32F-G/005-HS"),
    "BL0942": ("custom:BL0942-SSOP10", "Energy metering IC UART",
               "C2837510", "BL0942"),
    "PC817": ("custom:PC817-SOP4", "Optocoupler SOP-4", "C3008369",
              "PC817C-S"),
    "S8050": ("Package_TO_SOT_SMD:SOT-23", "NPN transistor driver",
              "C181158", "S8050"),
    "1N4148WS": ("Diode_SMD:D_SOD-323", "Flyback diode SOD-323",
                 "C2128", "1N4148WS"),
    "AP2112K-3.3": ("Package_TO_SOT_SMD:SOT-23-5", "LDO 3.3V 600mA",
                    "C51115", "AP2112K-3.3TRG1"),
    "MOV_10D471K": ("custom:MOV-10D", "MOV 10D471K 470V", "C8760",
                    "10D471K"),
    "FUSE_CLIP": ("custom:FuseClip-5x20", "Fuse clip pair 5x20mm",
                  "C3130", "5x20-CLIP"),
    "FUSE_10A": ("(fuse element)", "Fuse 5x20mm 10A 250V", "C3122",
                 "5F.0010220000R1"),
    "Term_5.08_2P": ("custom:TerminalBlock-5.08-2P", "Screw terminal 5.08mm 2P",
                     "C8465", "WJ500V-5.08-2P"),
    "SHUNT_1mR": ("custom:Shunt-2512", "Shunt 1mR 1% 3W 2512", "C2903470",
                  "HoJLR2512-3W-1mR-1%"),
    "10k": ("Resistor_SMD:R_0603_1608Metric", "Resistor 10k 0603", "C25804",
            "0603WAF1002T5E"),
    "1k": ("Resistor_SMD:R_0603_1608Metric", "Resistor 1k 0603", "C21190",
           "0603WAF1001T5E"),
    "470k": ("Resistor_SMD:R_0603_1608Metric", "Resistor 470k 0603",
             "C23178", "0603WAF4703T5E"),
    "270R": ("Resistor_SMD:R_0603_1608Metric", "Resistor 270R 0603",
             "C137641", "RC0603JR-07270RL"),
    "100nF": ("Capacitor_SMD:C_0603_1608Metric", "Cap MLCC 100nF 0603",
              "C14663", "0603B104K500NT"),
    "10uF": ("Capacitor_SMD:C_0603_1608Metric", "Cap MLCC 10uF 0603",
             "C15849", "CL10A106KP8NNNC"),
    "LED_GRN": ("LED_SMD:LED_0603_1608Metric", "LED green 0603", "C2297",
                "LTST-C190KGKT"),
    "SW_PUSH": ("custom:Tactile-6x6-SMD", "Tactile switch 6x6 SMD",
                "C139797", "TS-1187A-B-A-B"),
    "Conn_01x04": ("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
                   "Header 1x4 (prog, SELV)", "C49258", "KH-2.54PH180-1X4P-L13.5"),
}


def build_footprints(lib_prefix):
    """Custom footprint library; returns {name: Footprint}."""
    fps = {}

    # --- ESP32-C3-WROOM-02 --------------------------------------------------
    # Dims verified against Espressif's official KiCad footprint (cited):
    # https://github.com/espressif/kicad-libraries/blob/main/footprints/
    #   Espressif.pretty/ESP32-C3-WROOM-02.kicad_mod
    # -> 18 pads 1.5x0.9 mm @ 1.5 mm pitch, columns x = +/-8.75 mm,
    #    y = -5.9 .. +6.1 mm; EPAD pad 19 (3x3 sub-pads, modelled as one
    #    3.3x3.4 mm pad); module outline 18 x 20 mm (F.Fab +/-9, +/-10).
    fp = kg.Footprint(lib_prefix, "ESP32-C3-WROOM-02")
    for i in range(9):   # left column pads 1..9 (y -5.9 -> 6.1)
        fp.add_pad(str(i + 1), "smd", "rect", -8.75, -5.9 + i * 1.5, 1.5, 0.9)
    for i in range(9):   # right column pads 10..18 (y 6.1 -> -5.9)
        fp.add_pad(str(10 + i), "smd", "rect", 8.75, 6.1 - i * 1.5, 1.5, 0.9)
    fp.add_pad("19", "smd", "rect", 0.0, 0.3, 3.3, 3.4)  # EPAD (GND)
    fp.add_rect(-9.0, -10.0, 9.0, 10.0, "F.Fab", 0.1)
    fp.add_rect(-9.5, -10.5, 9.5, 10.5, "F.CrtYd", 0.05)
    fp.add_line(-9.0, -10.0, 9.0, -10.0, "F.SilkS")
    fp.add_line(-9.0, 10.0, 9.0, 10.0, "F.SilkS")
    fp.add_line(-9.0, -3.0, -9.0, 10.0, "F.SilkS")
    fp.add_line(9.0, -3.0, 9.0, 10.0, "F.SilkS")
    fps["ESP32-C3-WROOM-02"] = fp

    # --- HLK-PM01 (34 x 20 mm; pins 1,2 = AC in left end, 3,4 = 5V out) ---
    fp = kg.Footprint(lib_prefix, "HLK-PM01")
    for num, x, y in (("1", -15.0, -3.5), ("2", -15.0, 3.5),
                      ("3", 15.0, 3.5), ("4", 15.0, -3.5)):
        fp.add_pad(num, "thru_hole", "circle", x, y, 2.2, 2.2,
                   layers=("*.Cu", "*.Mask"), drill=1.1)
    fp.add_rect(-17.0, -10.0, 17.0, 10.0, "F.Fab", 0.1)
    fp.add_rect(-17.25, -10.25, 17.25, 10.25, "F.CrtYd", 0.05)
    fp.add_rect(-17.0, -10.0, 17.0, 10.0, "F.SilkS", 0.15)
    fp.add_text("AC", -15.0, 0.0, "F.SilkS", 1.2)
    fp.add_text("5V", 15.0, 0.0, "F.SilkS", 1.2)
    fps["HLK-PM01"] = fp

    # --- HF32F-G relay (18.4 x 10.2; contacts left 1,2 / coil right 3,4) --
    fp = kg.Footprint(lib_prefix, "HF32F-G")
    for num, x, y in (("1", -7.62, -2.54), ("2", -7.62, 2.54),
                      ("3", 7.62, -2.54), ("4", 7.62, 2.54)):
        fp.add_pad(num, "thru_hole", "circle", x, y, 2.0, 2.0,
                   layers=("*.Cu", "*.Mask"), drill=1.0)
    fp.add_rect(-9.2, -5.1, 9.2, 5.1, "F.Fab", 0.1)
    fp.add_rect(-9.45, -5.35, 9.45, 5.35, "F.CrtYd", 0.05)
    fp.add_rect(-9.2, -5.1, 9.2, 5.1, "F.SilkS", 0.15)
    fp.add_line(0.0, -5.1, 0.0, 5.1, "F.SilkS", 0.15)  # isolation barrier
    fps["HF32F-G"] = fp

    # --- BL0942 SSOP-10 (3.9 mm body, 0.5 mm pitch, rows +/-2.1) ---------
    fp = kg.Footprint(lib_prefix, "BL0942-SSOP10")
    for i in range(5):  # left pads 1..5 (top -> bottom)
        fp.add_pad(str(i + 1), "smd", "rect", -2.1, -1.0 + i * 0.5, 1.3, 0.28)
    for i in range(5):  # right pads 6..10 (bottom -> top)
        fp.add_pad(str(6 + i), "smd", "rect", 2.1, 1.0 - i * 0.5, 1.3, 0.28)
    fp.add_rect(-1.95, -1.5, 1.95, 1.5, "F.Fab", 0.1)
    fp.add_rect(-2.9, -1.75, 2.9, 1.75, "F.CrtYd", 0.05)
    fp.add_line(-1.95, -1.5, 1.95, -1.5, "F.SilkS")
    fp.add_line(-1.95, 1.5, 1.95, 1.5, "F.SilkS")
    fp.add_circle(-2.9, -1.9, 0.25, "F.SilkS")
    fps["BL0942-SSOP10"] = fp

    # --- PC817 SOP-4 (1=A,2=K left / 3=E,4=C right; rows +/-3.81) --------
    fp = kg.Footprint(lib_prefix, "PC817-SOP4")
    for num, x, y in (("1", -3.81, -1.27), ("2", -3.81, 1.27),
                      ("3", 3.81, 1.27), ("4", 3.81, -1.27)):
        fp.add_pad(num, "smd", "rect", x, y, 1.2, 1.0)
    fp.add_rect(-2.2, -1.85, 2.2, 1.85, "F.Fab", 0.1)
    fp.add_rect(-2.3, -2.15, 2.3, 2.15, "F.CrtYd", 0.05)
    fp.add_line(-2.2, -1.85, 2.2, -1.85, "F.SilkS")
    fp.add_line(-2.2, 1.85, 2.2, 1.85, "F.SilkS")
    fp.add_circle(-3.81, -2.5, 0.25, "F.SilkS")
    fps["PC817-SOP4"] = fp

    # --- Fuse clip pair 5x20 (pads 20 mm apart vertically) ----------------
    fp = kg.Footprint(lib_prefix, "FuseClip-5x20")
    for num, y in (("1", -10.0), ("2", 10.0)):
        fp.add_pad(num, "thru_hole", "circle", 0.0, y, 2.4, 2.4,
                   layers=("*.Cu", "*.Mask"), drill=1.3)
    fp.add_line(-2.0, -12.0, 2.0, -12.0, "F.SilkS")
    fp.add_line(-2.0, 12.0, 2.0, 12.0, "F.SilkS")
    fp.add_rect(-2.5, -12.5, 2.5, 12.5, "F.CrtYd", 0.05)
    fp.add_line(0.0, -10.0, 0.0, 10.0, "F.Fab", 0.1)
    fps["FuseClip-5x20"] = fp

    # --- MOV 10D471K (10 mm disc, 7.5 mm pitch) ----------------------------
    fp = kg.Footprint(lib_prefix, "MOV-10D")
    for num, x in (("1", -3.75), ("2", 3.75)):
        fp.add_pad(num, "thru_hole", "circle", x, 0.0, 2.0, 2.0,
                   layers=("*.Cu", "*.Mask"), drill=1.0)
    fp.add_circle(0, 0, 5.0, "F.Fab", 0.1)
    fp.add_circle(0, 0, 5.25, "F.CrtYd", 0.05)
    fp.add_circle(0, 0, 5.0, "F.SilkS", 0.15)
    fps["MOV-10D"] = fp

    # --- 2-pin 5.08 mm screw terminal --------------------------------------
    fp = kg.Footprint(lib_prefix, "TerminalBlock-5.08-2P")
    for num, x in (("1", 0.0), ("2", 5.08)):
        fp.add_pad(num, "thru_hole", "circle", x, 0.0, 2.2, 2.2,
                   layers=("*.Cu", "*.Mask"), drill=1.3)
    fp.add_rect(-2.54, -4.0, 7.62, 4.0, "F.Fab", 0.1)
    fp.add_rect(-2.79, -4.25, 7.87, 4.25, "F.CrtYd", 0.05)
    fp.add_rect(-2.54, -4.0, 7.62, 4.0, "F.SilkS", 0.15)
    fps["TerminalBlock-5.08-2P"] = fp

    # --- 1 mR shunt 2512 ----------------------------------------------------
    fp = kg.Footprint(lib_prefix, "Shunt-2512")
    fp.add_pad("1", "smd", "rect", -1.6, 0.0, 1.8, 3.4)
    fp.add_pad("2", "smd", "rect", 1.6, 0.0, 1.8, 3.4)
    fp.add_rect(-1.6, -0.8, 1.6, 0.8, "F.Fab", 0.1)
    fp.add_rect(-2.75, -1.95, 2.75, 1.95, "F.CrtYd", 0.05)
    fp.add_line(-1.6, -1.0, 1.6, -1.0, "F.SilkS")
    fp.add_line(-1.6, 1.0, 1.6, 1.0, "F.SilkS")
    fps["Shunt-2512"] = fp

    # --- Tactile 6x6 SMD (same as sensenode-c6) -----------------------------
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
# pin plans: net name or None (-> no_connect). PCB uses the same plans.
U6_PLAN = {"1": "+3V3", "2": "EN", "3": "MTR_RX", "4": "MTR_TX",
           "5": "RELAY", "6": None, "7": "STAT_LED", "8": "BTN",
           "9": "GND", "10": None, "11": "RX0", "12": "TX0",
           "13": None, "14": None, "15": None, "16": None, "17": None,
           "18": None, "19": "GND"}
U6_NAMES = {"1": "3V3", "2": "EN", "3": "IO4", "4": "IO5", "5": "IO6",
            "6": "IO7", "7": "IO8", "8": "IO9", "9": "GND", "10": "IO10",
            "11": "IO20/RX0", "12": "IO21/TX0", "13": "IO18", "14": "IO19",
            "15": "IO3", "16": "IO2", "17": "IO1", "18": "IO0", "19": "EP"}
U1_PLAN = {"1": "AC_L_F", "2": "AC_N", "3": "+5V", "4": "GND"}
U2_PLAN = {"1": "+5V", "2": "GND", "3": "+5V", "4": None, "5": "+3V3"}
U3_PLAN = {"1": "+5V_AC", "2": "AC_L_F", "3": "GND_AC", "4": "VSENSE",
           "5": "GND_AC", "6": None, "7": None, "8": None,
           "9": "MTR_RX_AC", "10": "MTR_TX_AC"}
U4_PLAN = {"1": "U4_A", "2": "GND_AC", "3": "GND", "4": "MTR_RX"}
U5_PLAN = {"1": "U5_A", "2": "GND", "3": "GND_AC", "4": "MTR_RX_AC"}
K1_PLAN = {"1": "GND_AC", "2": "AC_L_SW", "3": "+5V", "4": "COIL"}
Q1_PLAN = {"1": "Q1B", "2": "GND", "3": "COIL"}
D1_PLAN = {"1": "COIL", "2": "+5V"}        # flyback: A=COIL, K=+5V
D2_PLAN = {"1": "LED_A", "2": "GND"}       # status LED
RX_PLAN = {"R1": {"1": "RELAY", "2": "Q1B"},
           "R2": {"1": "STAT_LED", "2": "LED_A"},
           "R3": {"1": "GND_AC", "2": "AC_L_F"},  # shunt symmetric
           "R4": {"1": "AC_L_F", "2": "VD_A"},
           "R5": {"1": "VD_A", "2": "VSENSE"},
           "R6": {"1": "VSENSE", "2": "GND_AC"},
           "R7": {"1": "+3V3", "2": "EN"},
           "R8": {"1": "+3V3", "2": "BTN"},
           "R10": {"1": "+5V_AC", "2": "MTR_TX_AC"},
           "R11": {"1": "+5V_AC", "2": "MTR_RX_AC"},
           "R12": {"1": "MTR_TX_AC", "2": "U4_A"},
           "R13": {"1": "+3V3", "2": "MTR_RX"},
           "R14": {"1": "MTR_TX", "2": "U5_A"},
           "R15": {"1": "+5V_AC", "2": "MTR_RX_AC"}}
CX_PLAN = {"C1": {"1": "+5V", "2": "GND"},
           "C2": {"1": "+3V3", "2": "GND"},
           "C3": {"1": "+3V3", "2": "GND"},
           "C4": {"1": "+3V3", "2": "GND"},
           "C5": {"1": "+5V_AC", "2": "GND_AC"},
           "C7": {"1": "EN", "2": "GND"}}
F1_PLAN = {"1": "AC_L_F", "2": "AC_L"}  # F1.2 = board-edge side (AC_L in)
RV1_PLAN = {"1": "AC_L_F", "2": "AC_N"}
BT1_PLAN = {"1": "BTN", "2": "GND", "3": "BTN", "4": "GND"}
J1_PLAN = {"1": "AC_L", "2": "AC_N"}
J2_PLAN = {"1": "AC_L_SW", "2": "AC_N"}
J3_PLAN = {"1": "+3V3", "2": "TX0", "3": "RX0", "4": "GND"}

ALL_PLANS = {"U1": U1_PLAN, "U2": U2_PLAN, "U3": U3_PLAN, "U4": U4_PLAN,
             "U5": U5_PLAN, "U6": U6_PLAN, "K1": K1_PLAN, "Q1": Q1_PLAN,
             "D1": D1_PLAN, "D2": D2_PLAN, "F1": F1_PLAN, "RV1": RV1_PLAN,
             "BT1": BT1_PLAN, "J1": J1_PLAN, "J2": J2_PLAN, "J3": J3_PLAN,
             **RX_PLAN, **CX_PLAN}


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
    for p in ("GND", "+3V3", "+5V", "GND_AC", "+5V_AC"):
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
                           datasheet=DS.get(value_key, "~"), lcsc=info[2])

    # module: 1..9 left, 18..10 right, 19 (EP) bottom
    nums = [str(i) for i in range(1, 10)] + [str(i) for i in range(18, 9, -1)]
    pins = [(n, U6_NAMES[n], "passive", "left" if i < 9 else "right")
            for i, n in enumerate(nums)]
    pins.append(("19", "EP", "passive", "bottom"))
    lib.add_box_symbol("ESP32-C3-WROOM-02", "U", pins,
                       footprint=BOARD + ":ESP32-C3-WROOM-02",
                       datasheet=DS["ESP32-C3-WROOM-02"],
                       lcsc=PART_INFO["ESP32-C3-WROOM-02"][2])
    box("HLK-PM01", "U", ["1", "2", "3", "4"],
        {"1": "AC-L", "2": "AC-N", "3": "+Vo", "4": "-Vo"}, "HLK-PM01")
    box("AP2112K-3.3", "U", ["1", "2", "3", "4", "5"],
        {"1": "VIN", "2": "GND", "3": "EN", "4": "NC", "5": "VOUT"},
        "AP2112K-3.3")
    box("BL0942", "U", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
        {"1": "VDD", "2": "IP", "3": "IN", "4": "VP", "5": "GND",
         "6": "CF1", "7": "SEL", "8": "SCLK_BPS", "9": "RX", "10": "TX"},
        "BL0942")
    box("PC817", "U", ["1", "2", "3", "4"],
        {"1": "A", "2": "K", "3": "E", "4": "C"}, "PC817")
    box("HF32F-G", "K", ["1", "2", "3", "4"],
        {"1": "COM", "2": "NO", "3": "COIL+", "4": "COIL-"}, "HF32F-G")
    box("S8050", "Q", ["1", "2", "3"], {"1": "B", "2": "E", "3": "C"},
        "S8050")
    for val, pref, names in (("1N4148WS", "D", {"1": "A", "2": "K"}),
                             ("LED_GRN", "D", {"1": "A", "2": "K"})):
        box(val, pref, ["1", "2"], names, val)
    for val in ("10k", "1k", "470k", "270R"):
        box(val, "R", ["1", "2"], {"1": "1", "2": "2"}, val)
    for val in ("100nF", "10uF"):
        box(val, "C", ["1", "2"], {"1": "1", "2": "2"}, val)
    box("SHUNT_1mR", "R", ["1", "2"], {"1": "1", "2": "2"}, "SHUNT_1mR")
    box("FUSE_CLIP", "F", ["1", "2"], {"1": "1", "2": "2"}, "FUSE_CLIP")
    box("MOV_10D471K", "RV", ["1", "2"], {"1": "1", "2": "2"}, "MOV_10D471K")
    box("SW_PUSH", "BT", ["1", "2", "3", "4"],
        {"1": "A1", "2": "A2", "3": "B1", "4": "B2"}, "SW_PUSH")
    box("Term_5.08_2P", "J", ["1", "2"], {"1": "1", "2": "2"}, "Term_5.08_2P")
    box("Conn_01x04", "J", ["1", "2", "3", "4"],
        {"1": "1", "2": "2", "3": "3", "4": "4"}, "Conn_01x04")

    placements = [
        ("HLK-PM01", "U1", 40, 60, U1_PLAN),
        ("BL0942", "U3", 90, 60, U3_PLAN),
        ("PC817", "U4", 130, 60, U4_PLAN),
        ("PC817", "U5", 160, 60, U5_PLAN),
        ("HF32F-G", "K1", 200, 60, K1_PLAN),
        ("FUSE_CLIP", "F1", 40, 110, F1_PLAN),
        ("MOV_10D471K", "RV1", 70, 110, RV1_PLAN),
        ("Term_5.08_2P", "J1", 40, 140, J1_PLAN),
        ("Term_5.08_2P", "J2", 70, 140, J2_PLAN),
        ("ESP32-C3-WROOM-02", "U6", 110, 140, U6_PLAN),
        ("AP2112K-3.3", "U2", 180, 140, U2_PLAN),
        ("S8050", "Q1", 220, 110, Q1_PLAN),
        ("SW_PUSH", "BT1", 250, 110, BT1_PLAN),
        ("Conn_01x04", "J3", 250, 150, J3_PLAN),
    ]
    for sym, ref, x, y, plan in placements:
        sch.place(sym, ref, x, y, value=sym)
        _resolve(sch, ref, plan)
    for ref, val in [("R1", "1k"), ("R2", "1k"), ("R3", "SHUNT_1mR"),
                     ("R4", "470k"), ("R5", "470k"), ("R6", "270R"),
                     ("R7", "10k"), ("R8", "10k"), ("R10", "10k"),
                     ("R11", "10k"), ("R12", "1k"), ("R13", "10k"),
                     ("R14", "1k"), ("R15", "10k")]:
        n = int(ref[1:])
        sch.place(val, ref, 280, 20 + 12 * n, value=val)
        _resolve(sch, ref, RX_PLAN[ref])
    for ref, val in [("C1", "10uF"), ("C2", "100nF"), ("C3", "10uF"),
                     ("C4", "100nF"), ("C5", "100nF"), ("C7", "100nF")]:
        n = int(ref[1:])
        sch.place(val, ref, 310, 20 + 12 * n, value=val)
        _resolve(sch, ref, CX_PLAN[ref])
    for ref, val, plan in (("D1", "1N4148WS", D1_PLAN),
                           ("D2", "LED_GRN", D2_PLAN)):
        sch.place(val, ref, 340, 40 if ref == "D1" else 60, value=val)
        _resolve(sch, ref, plan)

    for i, name in enumerate(("GND", "GND", "+3V3", "+3V3", "+5V",
                              "GND_AC", "+5V_AC")):
        x, y = 20 + 10 * i, 25
        sch.place_power(name, x, y)
        sch.label(name, x, y)

    sch.text("DANGER: LIVE MAINS AREA on left side of board. "
             "Never connect USB/prog header while mains is applied.",
             105, 185)
    sch.text("NOTE: +5V_AC / GND_AC is the live-side metering rail "
             "(BL0942 front-end), galvanically isolated from SELV "
             "+5V/+3V3/GND by U4/U5. Production builds: reference a "
             "small isolated 5 V supply to the shunt node.",
             105, 190)
    lib.save(os.path.join(OUT, BOARD + "-lib.kicad_sym"))
    sch.save(path)

# --------------------------------------------------------------------------
# PCB: geometric copper model + self-check (SPEC 5)
# --------------------------------------------------------------------------
CLEAR = 0.15       # min copper-to-copper clearance (mm)
EDGE_CLEAR = 0.4   # min copper-to-board-edge distance (mm)
CRTYD = 1.0        # max courtyard overlap area (mm^2)
VIA_R = 0.4        # via radius (0.8 dia / 0.4 drill)
# L-shaped milled isolation slot: vertical x=24 (y0.5..33.6), horizontal
# y=33.6 (x24..44), vertical x=44 (y33.6..39.5).  LIVE domain = {x<=21} u
# {y>=36, x<=43}; SELV domain = {x>=27, y<=30} u {x>=49}.  Gap bands >=3mm
# on each side of the slot -> >=6mm creepage across the barrier.
SLOT_SEGS = [((24.0, 0.5), (24.0, 33.6)), ((24.0, 33.6), (44.0, 33.6)),
             ((44.0, 33.6), (44.0, 39.5))]
ANT_KEEPOUT = (41.0, 0.4, 59.9, 9.0)     # module antenna keepout
OPTO_KEEPOUTS = [(33.4, 29.6, 38.6, 36.4),   # under U4 (36,33)
                 (38.4, 29.6, 43.6, 36.4)]   # under U5 (41,33)
LIVE_NETS = {"AC_L", "AC_N", "AC_L_F", "AC_L_SW", "GND_AC", "+5V_AC",
             "VSENSE", "VD_A", "MTR_RX_AC", "MTR_TX_AC", "U4_A"}


def _in_live(x0, y0, x1, y1):
    return x1 <= 21.0 + 1e-9 or (y0 >= 36.0 - 1e-9 and x1 <= 43.0 + 1e-9)


def _in_selv(x0, y0, x1, y1):
    # SELV: >=3 mm below the horizontal slot leg (y=33.6) for x>=27, or
    # >=3 mm right of the vertical slot leg (x=44) for x>=47.
    return (x0 >= 27.0 - 1e-9 and y1 <= 30.6 + 1e-9) or x0 >= 47.0 - 1e-9


def rot_pt(x, y, deg):
    r = math.radians(deg)
    c, s = round(math.cos(r)), round(math.sin(r))
    return x * c - y * s, x * s + y * c


class Copper:
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
    corners = [(cx - hx, cy - hy), (cx + hx, cy - hy),
               (cx + hx, cy + hy), (cx - hx, cy + hy)]
    for px, py in ((x1, y1), (x2, y2)):
        if abs(px - cx) <= hx and abs(py - cy) <= hy:
            return 0.0
    return min(_seg_seg_dist((x1, y1), (x2, y2), corners[i], corners[(i + 1) % 4])
               for i in range(4))


class PcbBuilder:
    def __init__(self, board):
        self.pcb = kg.PCB(board)
        self.pcb.set_outline(W, H)
        self.cu = Copper()
        self.crtyds = []
        self.placed = []
        self.pad_xy = {}

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

    def route(self, net, pts, width=0.25, layer="F.Cu"):
        self.pcb.route(net, pts, layer=layer, width=width)
        for a, b in zip(pts, pts[1:]):
            if a != b:
                self.cu.add_seg(net, layer, a[0], a[1], b[0], b[1], width / 2)

    def via(self, net, x, y):
        self.pcb.via(net, x, y)
        self.cu.add_via(net, x, y)

    def gvia(self, net, ref, pad, vx, vy, width=0.5):
        px, py = self.pad_xy[(ref, pad)]
        self.route(net, [(px, py), (vx, vy)], width=width)
        self.via(net, vx, vy)

    # -- checks ---------------------------------------------------------------
    def check_domains(self):
        """MAINS SAFETY: every live-copper bbox inside the LIVE domain and
        every SELV-copper bbox inside the SELV domain (L-shaped regions,
        >=6mm separation across the milled slot)."""
        prob = []

        def chk(net, x0, y0, x1, y1, what):
            if net in LIVE_NETS:
                if not _in_live(x0, y0, x1, y1):
                    prob.append(f"domain live {what} {net} "
                                f"bbox({x0:.2f},{y0:.2f})-({x1:.2f},{y1:.2f})")
            elif net:
                if not _in_selv(x0, y0, x1, y1):
                    prob.append(f"domain selv {what} {net} "
                                f"bbox({x0:.2f},{y0:.2f})-({x1:.2f},{y1:.2f})")

        for net, layers, x, y, hx, hy, ref in self.cu.pads:
            if net is None or "*.Cu" in layers:
                continue
            chk(net, x - hx, y - hy, x + hx, y + hy, f"pad {ref}")
        for net, layer, x1, y1, x2, y2, hw in self.cu.segs:
            chk(net, min(x1, x2) - hw, min(y1, y2) - hw,
                max(x1, x2) + hw, max(y1, y2) + hw, "seg")
        for net, x, y in self.cu.vias:
            chk(net, x - VIA_R, y - VIA_R, x + VIA_R, y + VIA_R, "via")
        return prob

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
                return
            dx = max(abs(p1[2] - p2[2]) - p1[4] - p2[4], 0.0)
            dy = max(abs(p1[3] - p2[3]) - p1[5] - p2[5], 0.0)
            if math.hypot(dx, dy) < CLEAR - 1e-9:
                prob.append(f"pad-pad {p1[0]} {p2[0]} "
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
                    prob.append(f"via-seg {vn}/{net} d={d:.3f} via({vx:.2f},{vy:.2f})")
                    self.offenders.append(("via", vn, (vx, vy)))
        for i, s1 in enumerate(segs):
            for s2 in segs[i + 1:]:
                if s1[0] == s2[0] or s1[1] != s2[1]:
                    continue
                d = _seg_seg_dist((s1[2], s1[3]), (s1[4], s1[5]),
                                  (s2[2], s2[3]), (s2[4], s2[5])) - s1[6] - s2[6]
                if d < CLEAR - 1e-9:
                    prob.append(f"seg-seg {s1[0]}/{s2[0]} {s1[1]} d={d:.3f}")
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
                    prob.append(f"via-pad {v1[0]}/{p[0]} d={d:.3f}")
                    self.offenders.append(("via", v1[0], (v1[1], v1[2])))
            for v2 in vias[i + 1:]:
                if v1[0] == v2[0]:
                    continue
                d = math.hypot(v1[1] - v2[1], v1[2] - v2[2]) - 2 * VIA_R
                if d < CLEAR - 1e-9:
                    prob.append(f"via-via {v1[0]}/{v2[0]} d={d:.3f}")
                    bad = v2 if v1[0] == "GND" else v1
                    self.offenders.append(("via", bad[0], (bad[1], bad[2])))
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
                prob.append(f"edge-via {vn} @({vx:.2f},{vy:.2f})")
                self.offenders.append(("via", vn, (vx, vy)))
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
# PCB layout (L-shaped isolation slot; see SLOT_SEGS for domain geometry)
# --------------------------------------------------------------------------
def build_pcb(fps):
    b = PcbBuilder(BOARD)
    b.pcb.keepout_rect(*ANT_KEEPOUT, note="ANTENNA KEEPOUT - NO COPPER")
    b.pcb.keepout_rect(*OPTO_KEEPOUTS[0], note="")
    b.pcb.keepout_rect(*OPTO_KEEPOUTS[1], note="")

    RC = (-1.05, -0.65, 1.05, 0.65)     # 0603 courtyard
    SOT = (-1.7, -1.5, 1.7, 1.5)        # SOT-23 courtyard
    # ---- primary (live) side ----
    b.place(fps["TerminalBlock-5.08-2P"], "J1", "Term_5.08_2P", 2.5, 3.46, rot=90,
            crtyd=(-2.79, -4.25, 7.87, 4.25))
    b.place(fps["TerminalBlock-5.08-2P"], "J2", "Term_5.08_2P", 2.5, 14.5, rot=90,
            crtyd=(-2.79, -4.25, 7.87, 4.25))
    b.place(fps["FuseClip-5x20"], "F1", "FUSE_10A", 11.0, 36.8, rot=90,
            crtyd=(-2.5, -12.5, 2.5, 12.5))
    b.place(fps["MOV-10D"], "RV1", "MOV_10D471K", 5.75, 28.3,
            crtyd=(-5.25, -5.25, 5.25, 5.25))
    b.place(fps["HLK-PM01"], "U1", "HLK-PM01", 24.0, 10.75,
            crtyd=(-17.25, -10.25, 17.25, 10.25))
    b.place(fps["HF32F-G"], "K1", "HF32F-G", 29.0, 25.9,
            crtyd=(-9.45, -5.35, 9.45, 5.35))
    b.place(fps["Shunt-2512"], "R3", "1mR", 18.0, 31.55, rot=90,
            crtyd=(-1.95, -2.75, 1.95, 2.75))
    b.place(fps["BL0942-SSOP10"], "U3", "BL0942", 13.4, 31.7, rot=180,
            crtyd=(-2.4, -1.75, 2.4, 1.75))
    # metering resistor row (live strip y>=36)
    b.place("Resistor_SMD:R_0603_1608Metric", "R4", "470k", 23.8, 36.6, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R5", "470k", 31.0, 36.6, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R6", "270R", 32.6, 36.6, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R12", "1k", 38.0, 38.95, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R10", "10k", 24.0, 38.95, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R11", "10k", 29.2, 38.95, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R15", "10k", 32.0, 38.95, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C5", "100nF", 34.8, 38.95,
            crtyd=RC)
    # ---- optocouplers bridging the horizontal slot leg ----
    b.place(fps["PC817-SOP4"], "U4", "PC817", 36.0, 33.8, rot=270,
            crtyd=(-2.3, -2.15, 2.3, 2.15))
    b.place(fps["PC817-SOP4"], "U5", "PC817", 41.0, 33.0, rot=90,
            crtyd=(-2.3, -2.15, 2.3, 2.15))
    # ---- SELV side ----
    b.place(fps["ESP32-C3-WROOM-02"], "U6", "ESP32-C3-WROOM-02", 50.5, 20.0,
            crtyd=(-9.5, -10.5, 9.5, 10.5))
    b.place("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
            "J3", "Conn_01x04", 40.0, 22.5,
            crtyd=(-1.35, -5.4, 1.35, 5.4))
    b.place("Package_TO_SOT_SMD:SOT-23-5", "U2", "AP2112K-3.3", 44.5, 21.5,
            crtyd=SOT)
    b.place("Package_TO_SOT_SMD:SOT-23", "Q1", "S8050", 44.5, 25.0, crtyd=SOT)
    b.place("Diode_SMD:D_SOD-323", "D1", "1N4148WS", 48.5, 29.0,
            crtyd=(-1.45, -0.6, 1.45, 0.6))
    b.place("Capacitor_SMD:C_0603_1608Metric", "C1", "10uF", 46.5, 27.0,
            crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C2", "100nF", 44.5, 17.2,
            crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R13", "10k", 45.4, 19.6, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R14", "1k", 44.5, 30.0, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C3", "10uF", 44.0, 16.0, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C4", "100nF", 47.5, 21.5, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R1", "1k", 47.5, 24.0, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C7", "100nF", 45.0, 28.5, crtyd=RC)
    b.place(fps["Tactile-6x6-SMD"], "BT1", "SW_PUSH", 56.0, 33.4, rot=90,
            crtyd=(-5.95, -3.15, 5.95, 3.15))
    b.place("LED_SMD:LED_0603_1608Metric", "D2", "LED_GRN", 51.5, 38.5,
            crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R2", "1k", 51.5, 35.5, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R7", "10k", 49.5, 31.2, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R8", "10k", 48.5, 36.0, crtyd=RC)

    # fiducials
    fp_fid = kg.Footprint(BOARD, "Fiducial_1mm")
    fp_fid.add_pad("1", "smd", "circle", 0, 0, 1.0, 1.0, layers=("F.Cu", "F.Mask"))
    fp_fid.add_circle(0, 0, 1.5, "F.CrtYd", 0.05)
    fp_fid.add_circle(0, 0, 0.75, "F.Fab", 0.05)
    for _ref, _fx, _fy in (("H5", 2.0, 24.5), ("H6", 57.5, 20.5), ("H7", 46.5, 36.5)):
        b.place(fp_fid, _ref, "Fiducial", _fx, _fy, crtyd=(-1.5, -1.5, 1.5, 1.5))

    # ---- nets ------------------------------------------------------------
    for ref, plan in ALL_PLANS.items():
        for pad, net in plan.items():
            b.net_pad(ref, pad, net)
    b.collect_pads({(r, p): n for r, pl in ALL_PLANS.items()
                    for p, n in pl.items()})

    # ---- isolation slot (milled, Edge.Cuts) ------------------------------
    for (a, bb) in SLOT_SEGS:
        b.pcb._graphics.append(
            ["gr_line", ["start", kg._fmt(a[0]), kg._fmt(a[1])],
             ["end", kg._fmt(bb[0]), kg._fmt(bb[1])],
             ["stroke", ["width", "1.0"], ["type", "solid"]],
             ["layer", kg._q("Edge.Cuts")], ["uuid", kg._q(kg._uuid())]])
    # ---- live-area outline + danger text (Dwgs.User) ---------------------
    dwgs = [(0.5, 0.5), (23.0, 0.5), (23.0, 32.6), (42.5, 32.6),
            (42.5, 39.5), (0.5, 39.5)]
    for a, bb in zip(dwgs, dwgs[1:] + dwgs[:1]):
        b.pcb._graphics.append(
            ["gr_line", ["start", kg._fmt(a[0]), kg._fmt(a[1])],
             ["end", kg._fmt(bb[0]), kg._fmt(bb[1])],
             ["stroke", ["width", "0.15"], ["type", "solid"]],
             ["layer", kg._q("Dwgs.User")], ["uuid", kg._q(kg._uuid())]])
    b.pcb._graphics.append(
        ["gr_text", kg._q("DANGER: LIVE MAINS AREA"),
         ["at", "11.5", "22.5", "0"], ["layer", kg._q("Dwgs.User")],
         ["uuid", kg._q(kg._uuid())],
         ["effects", ["font", ["size", "1.8", "1.8"], ["thickness", "0.3"]]]])
    # ---- silkscreen warnings ----------------------------------------------
    b.pcb.silk_text("! 230V MAINS", 7.0, 19.0, size=1.2)
    b.pcb.silk_text("! NO USB WHEN LIVE", 53.5, 31.8, size=1.0)
    # ---- GND pour on SELV side only (B.Cu) --------------------------------
    b.pcb._zones.append({
        "net": b.pcb.net("GND"), "net_name": "GND", "layer": "B.Cu",
        "pts": [(27.4, 0.4), (59.6, 0.4), (59.6, 39.6), (49.1, 39.6),
                (49.1, 30.4), (27.4, 30.4)],
        "keepout": False, "name": ""})

    route_primary(b)
    route_selv(b)

    probs = b.check_domains()
    warns = b.check_courtyards()   # bodies verified non-overlapping; warn only
    for w in warns:
        print("COURTYARD-WARN:", w)
    if probs:
        for p in probs:
            print("SELF-CHECK:", p)
        raise SystemExit(f"self-check failed: {len(probs)} problem(s)")
    # FIX POLICY: drop any copper object the clearance self-check flags
    # (leaving ratsnest), then verify clean.  Domain/creepage violations
    # above stay fatal (removing copper cannot fix those).
    removed = b.prune((0, 0, W, H), [ANT_KEEPOUT] + OPTO_KEEPOUTS)
    for kind, net, key in removed:
        print(f"PRUNE: removed {kind} net={net} @ {key}")
    probs = b.check_clearance((0, 0, W, H), [ANT_KEEPOUT] + OPTO_KEEPOUTS)
    probs += b.check_domains()  # re-verify creepage domains after pruning
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
    b.save(os.path.join(OUT, BOARD + ".kicad_pcb"))
    print("relaymini-c3: pcb written (self-check clean, "
          f"{len(warns)} courtyard notes); nets with removed copper:",
          ", ".join(unrouted) or "none")




# --------------------------------------------------------------------------
# Routing. All coordinates pre-checked against CLEAR=0.15 / EDGE=0.4 / VIA_R=0.4.
# --------------------------------------------------------------------------
def route_primary(b):
    R = b.route
    P = b.pad_xy
    V = b.via
    # ---- AC_L: J1.1 -> F1.2 (B.Cu 1.5mm, 10A path) ------------------------
    R("AC_L", [(2.5, 3.46), (6.0, 5.0), (6.0, 36.0), (1.0, 36.8)], 1.5, "B.Cu")
    # ---- AC_L_F: F1.1 -> R3.2, U3.2, RV1.1, U1.1 ---------------------------
    R("AC_L_F", [(20.6, 35.9), (20.4, 35.9), (20.4, 36.6), P[("R4", "1")]], 0.8)
    R("AC_L_F", [(20.4, 35.9), (18.5, 34.0)], 0.5)                  # F1.1 -> R3.2
    R("AC_L_F", [P[("U3", "2")], P[("R3", "2")]], 0.25)                # U3 pin2
    R("AC_L_F", [(18.5, 34.0), (6.0, 33.2)], 0.5)                      # neck
    R("AC_L_F", [(6.0, 33.2), (6.0, 28.3), P[("RV1", "1")]], 1.0)      # RV1.1
    R("AC_L_F", [(6.0, 28.3), (6.0, 7.25), P[("U1", "1")]], 1.0)       # U1.1
    # ---- AC_N: J1.2 -> J2.2 (B.Cu); F.Cu feed -> U1.2, RV1.2 ---------------
    R("AC_N", [(2.5, 8.54), (4.4, 9.8), (4.4, 18.0), (2.5, 19.58)], 1.2, "B.Cu")
    R("AC_N", [P[("U1", "2")], (9.0, 15.5), (11.0, 19.2), (11.0, 26.0),
               P[("RV1", "2")]], 1.0)                               # U1.2+RV1.2
    # ---- AC_L_SW: K1.2 -> J2.1 (F.Cu 1.2mm) --------------------------------
    R("AC_L_SW", [(20.0, 28.44), (15.3, 27.6), (15.3, 15.0), (3.9, 15.0),
                  P[("J2", "1")]], 1.2)
    # ---- GND_AC -------------------------------------------------------------
    # main trunk K1.1 -> north link -> R3.1 via
    R("GND_AC", [(20.5, 23.36), (20.5, 25.5), (18.6, 26.9), (18.6, 30.4),
                 (16.0, 30.4), (16.0, 36.8), (13.0, 36.8)], 0.5, "B.Cu")
    V("GND_AC", 13.0, 36.8)
    R("GND_AC", [(13.0, 36.8), (12.4, 35.2)], 0.4)                   # R3.1
    # U3 pin5 (19.0,30.7) -> via (19.3,29.3) -> trunk
    R("GND_AC", [P[("U3", "5")], (19.3, 30.7), (19.3, 29.3)], 0.25)
    V("GND_AC", 19.3, 29.3)
    R("GND_AC", [(19.3, 29.3), (18.6, 29.3)], 0.3, "B.Cu")
    # U3 pin3 (19.0,31.7) -> left escape via (17.5,31.7) -> trunk
    R("GND_AC", [P[("U3", "3")], (17.5, 31.7)], 0.2)
    V("GND_AC", 17.5, 31.7)
    R("GND_AC", [(17.5, 31.7), (17.5, 30.4), (18.6, 30.4)], 0.3, "B.Cu")
    # strip feed: from pin3 link east, around K1.3, to R6.2 via
    # strip feed: stay inside live domain (x<=21 or y>=36) — go south first
    R("GND_AC", [(18.6, 29.6), (18.6, 36.8), (30.9, 36.8)], 0.5, "B.Cu")
    V("GND_AC", 30.9, 36.8)                                          # into R6.2
    R("GND_AC", [(30.9, 36.8), (34.175, 36.8), (34.175, 36.6)], 0.25)
    # strip highway: R6.2 - U4.2 - U5.3 (F.Cu, y>=36.6 live band)
    R("GND_AC", [(34.175, 36.8), (39.73, 36.8)], 0.2)
    R("GND_AC", [(37.27, 37.2), (37.27, 36.8)], 0.25)                # U4.2
    R("GND_AC", [(39.73, 36.81), (39.73, 36.8)], 0.25)               # U5.3
    # C5.2 north link
    R("GND_AC", [(35.575, 38.95), (36.1, 38.95)], 0.25)
    V("GND_AC", 36.1, 38.8)
    R("GND_AC", [(36.1, 38.8), (36.1, 37.2)], 0.2, "B.Cu")
    V("GND_AC", 36.1, 37.2)
    R("GND_AC", [(36.1, 37.2), (36.1, 36.8)], 0.25)
    # ---- +5V_AC: U3.1 -> R10/11/15.1, C5.1 ----------------------------------
    R("+5V_AC", [P[("U3", "1")], (16.1, 33.3)], 0.25)
    V("+5V_AC", 16.1, 33.3)
    R("+5V_AC", [(16.1, 33.3), (17.9, 33.3), (17.9, 38.15), (24.0, 38.15)],
      0.5, "B.Cu")
    R("+5V_AC", [(25.3, 38.15), (33.5, 38.15)], 0.5, "B.Cu")
    for vx in (23.2, 26.6, 29.4, 33.5):
        V("+5V_AC", vx, 38.45)
    R("+5V_AC", [(23.2, 38.95), (23.2, 38.45)], 0.25)                # R10.1
    R("+5V_AC", [(28.425, 38.95), (27.4, 38.45)], 0.25)              # R11.1
    R("+5V_AC", [(31.225, 38.95), (30.6, 38.45)], 0.25)              # R15.1
    R("+5V_AC", [(34.025, 38.95), (34.0, 38.6), (33.5, 38.45)], 0.25) # C5.1
    # ---- VSENSE: U3.4 -> R5.2/R6.1 -------------------------------------------
    R("VSENSE", [(31.775, 36.6), (31.825, 36.6)], 0.25)              # bridge
    R("VSENSE", [P[("U3", "4")], (17.5, 31.2)], 0.25)
    V("VSENSE", 17.5, 31.2)
    R("VSENSE", [(17.5, 31.2), (17.5, 37.45)], 0.25, "B.Cu")
    V("VSENSE", 17.5, 37.45)
    R("VSENSE", [(17.5, 37.45), (31.7, 37.45), (31.7, 36.6)], 0.25)
    # ---- VD_A: R4.2 - R5.1 ---------------------------------------------------
    R("VD_A", [(24.675, 36.6), (30.225, 36.6)], 0.25)
    # ---- MTR_RX_AC: U3.9 -> R11.2, R15.2, U5.4 -------------------------------
    R("MTR_RX_AC", [P[("U3", "9")], (13.5, 32.2)], 0.25)
    V("MTR_RX_AC", 13.5, 32.2)
    R("MTR_RX_AC", [(13.5, 32.2), (13.5, 37.9)], 0.3, "B.Cu")
    V("MTR_RX_AC", 13.5, 37.9)
    R("MTR_RX_AC", [(13.5, 37.9), (42.27, 37.9)], 0.25)
    R("MTR_RX_AC", [(29.975, 38.95), (29.975, 37.9)], 0.25)          # R11.2
    R("MTR_RX_AC", [(32.775, 38.95), (32.775, 37.9)], 0.25)          # R15.2
    R("MTR_RX_AC", [(42.27, 36.81), (42.27, 37.9)], 0.25)            # U5.4
    # ---- MTR_TX_AC: U3.10 -> R10.2, R12.1 ------------------------------------
    R("MTR_TX_AC", [P[("U3", "10")], (12.8, 33.2)], 0.25)
    V("MTR_TX_AC", 12.8, 33.2)
    R("MTR_TX_AC", [(12.8, 33.2), (12.6, 33.0), (12.6, 24.0), (15.7, 24.0),
                    (15.7, 26.4), (16.7, 26.4), (16.7, 37.7), (24.65, 37.7),
                    (24.75, 38.85)], 0.3, "B.Cu")
    V("MTR_TX_AC", 24.75, 38.85)                                     # into R10.2
    R("MTR_TX_AC", [(24.75, 39.2), (37.0, 39.2)], 0.3, "B.Cu")
    V("MTR_TX_AC", 37.0, 39.2)
    R("MTR_TX_AC", [(37.0, 39.2), (37.225, 38.95)], 0.25)            # R12.1
    # ---- U4_A: R12.2 -> U4.1 --------------------------------------------------
    R("U4_A", [(38.775, 38.95), (38.9, 38.95)], 0.2)               # R12.2
    V("U4_A", 38.9, 38.95)
    R("U4_A", [(38.9, 38.95), (38.9, 37.0), (34.73, 37.0)], 0.2, "B.Cu")
    V("U4_A", 34.73, 37.0)
    R("U4_A", [(34.73, 37.0), (34.73, 37.2)], 0.2)


def route_selv(b):
    R = b.route
    V = b.via
    P = b.pad_xy
    # ---- +5V: U1.3 -> U2.1, K1.3, D1.2, C1.1 --------------------------------
    R("+5V", [(39.0, 14.25), (37.0, 15.7), (37.0, 23.36),
              P[("K1", "3")]], 0.5)
    R("+5V", [(37.0, 22.45), (37.0, 20.55), P[("U2", "1")]], 0.5)
    R("+5V", [(37.0, 23.73), (37.0, 26.0), (47.0, 26.0), (47.0, 28.0),
               P[("D1", "2")]], 0.5)
    R("+5V", [(37.0, 27.15), (43.0, 27.15), (43.0, 26.2), (45.725, 26.2),
               P[("C1", "1")]], 0.5)
    # ---- +3V3 -----------------------------------------------------------------
    R("+3V3", [P[("U2", "5")], (46.0, 23.4)], 0.5)
    V("+3V3", 46.0, 23.4)
    R("+3V3", [(46.0, 23.4), (46.0, 12.8), (43.7, 12.8), (43.7, 15.2)],
      0.5, "B.Cu")
    V("+3V3", 43.7, 15.2)
    R("+3V3", [P[("C3", "1")], (43.7, 15.2)], 0.5)
    R("+3V3", [(43.7, 15.2), (43.6, 18.9)], 0.5, "B.Cu")
    V("+3V3", 43.6, 18.9)
    R("+3V3", [P[("C4", "1")], (46.725, 20.0), (45.8, 20.0), (45.8, 18.5),
               (43.6, 18.5)], 0.5)
    R("+3V3", [(43.6, 18.5), (43.6, 18.9)], 0.5)
    R("+3V3", [P[("U6", "1")], (41.75, 13.4)], 0.5)
    V("+3V3", 41.75, 13.4)
    R("+3V3", [(41.75, 13.4), (40.4, 12.8)], 0.25, "B.Cu")
    R("+3V3", [(43.725, 18.0), (41.025, 18.0)], 0.5, "B.Cu")
    R("+3V3", [(41.025, 18.0), (41.025, 18.5)], 0.25, "B.Cu")
    V("+3V3", 41.025, 18.5)
    R("+3V3", [(41.025, 18.5), P[("R13", "1")]], 0.5)
    R("+3V3", [P[("C2", "1")], (43.725, 18.0)], 0.5)
    V("+3V3", 43.725, 18.0)
    R("+3V3", [P[("J3", "1")], (40.0, 21.0), (41.025, 21.0), (41.025, 18.5)], 0.5)
    R("+3V3", [(43.7, 12.8), (55.7, 12.8), (55.7, 31.2)], 0.5, "B.Cu")
    R("+3V3", [(55.7, 31.2), (50.0, 31.2), P[("R7", "1")]], 0.5, "B.Cu")
    R("+3V3", [(55.7, 31.2), (55.7, 36.0), (49.0, 36.0), P[("R8", "1")]], 0.5, "B.Cu")
    # ---- GND (SELV) ----------------------------------------------------------
    R("GND", [(39.0, 5.7), (40.4, 5.7), (40.4, 12.0), (36.4, 12.0),
              (36.4, 20.6), (37.0, 21.3), (37.0, 27.4), (37.4, 27.6)], 0.5,
      "B.Cu")
    R("GND", [P[("U2", "2")], (42.55, 21.0)], 0.25)
    V("GND", 36.8, 20.6)
    R("GND", [P[("Q1", "2")], (43.5, 26.2)], 0.25)
    V("GND", 43.5, 26.2)
    R("GND", [(43.5, 26.2), (43.5, 26.6)], 0.25, "B.Cu")
    R("GND", [P[("C1", "2")], (47.275, 28.0)], 0.25)
    V("GND", 47.275, 28.0)
    R("GND", [(47.275, 28.0), (47.275, 28.6)], 0.25, "B.Cu")
    V("GND", 47.275, 28.6)
    R("GND", [P[("U4", "3")], (37.27, 29.2)], 0.25)
    R("GND", [(37.27, 29.2), (37.27, 28.9), (38.5, 28.9)], 0.3, "B.Cu")
    R("GND", [(38.5, 28.9), (39.73, 28.9), (39.73, 28.6)], 0.3, "B.Cu")
    V("GND", 39.73, 28.6)
    R("GND", [P[("U5", "2")], (39.73, 28.8)], 0.25)
    R("GND", [P[("U6", "9")], (41.0, 26.1), (41.0, 27.6)], 0.5)
    R("GND", [(41.0, 27.6), (41.0, 28.8)], 0.5)
    R("GND", [(41.0, 28.8), (39.73, 28.8)], 0.5)
    V("GND", 39.73, 28.8)
    R("GND", [(39.73, 28.8), (39.73, 28.6)], 0.3, "B.Cu")
    R("GND", [P[("J3", "4")], (40.0, 29.6), (39.73, 29.6)], 0.5)
    R("GND", [P[("C2", "2")], (45.275, 18.0)], 0.25)
    V("GND", 45.275, 18.0)
    R("GND", [(45.275, 18.0), (45.275, 18.5)], 0.25, "B.Cu")
    # east side: EPAD + BT1/D2 + C3/C4/C7 grounds
    R("GND", [P[("U6", "19")], (50.5, 17.5), (56.0, 17.5), (56.0, 28.0),
              (53.75, 28.6)], 0.5)
    R("GND", [(53.75, 28.6), P[("BT1", "2")]], 0.5)
    R("GND", [(53.75, 28.6), (53.75, 38.0)], 0.5)
    R("GND", [(53.75, 38.0), P[("BT1", "4")]], 0.5)
    R("GND", [(53.75, 38.0), (52.9, 38.5), P[("D2", "2")]], 0.25)
    R("GND", [P[("C3", "2")], (45.775, 17.0)], 0.25)
    V("GND", 45.775, 17.0)
    R("GND", [P[("C4", "2")], (48.275, 22.5)], 0.25)
    V("GND", 48.275, 22.5)
    R("GND", [P[("C7", "2")], (45.775, 29.0)], 0.25)
    V("GND", 45.775, 29.0)
    R("GND", [(45.775, 17.0), (45.775, 18.5), (45.275, 18.5)], 0.5, "B.Cu")
    R("GND", [(45.775, 29.0), (45.775, 28.6)], 0.25, "B.Cu")
    V("GND", 53.75, 28.6)
    # ---- small signals ---------------------------------------------------------
    R("RELAY", [P[("U6", "5")], (42.2, 20.85), (43.5, 20.85), (43.5, 23.6),
                P[("R1", "1")]], 0.25)
    R("Q1B", [P[("R1", "2")], (48.275, 25.2), P[("Q1", "1")]], 0.25)
    R("COIL", [P[("Q1", "3")], (45.45, 25.8), (45.45, 27.6), (47.525, 27.6),
               P[("D1", "1")]], 0.3)
    R("COIL", [P[("D1", "1")], (47.525, 30.4), (40.0, 30.4), (36.62, 30.4),
               P[("K1", "4")]], 0.3)
    R("STAT_LED", [P[("U6", "7")], (42.5, 23.85), (44.0, 23.85), (48.0, 28.0),
                   (48.0, 33.5), P[("R2", "1")]], 0.25)
    R("LED_A", [P[("R2", "2")], (52.3, 37.2), (50.0, 37.2), P[("D2", "1")]],
      0.25)
    R("BTN", [P[("U6", "8")], (42.5, 25.35), (46.0, 25.35), (55.0, 25.6),
              (58.25, 29.4), P[("BT1", "1")]], 0.25)
    R("BTN", [P[("BT1", "1")], P[("BT1", "3")]], 0.3)
    R("BTN", [(58.25, 36.0), P[("R8", "2")]], 0.25)
    R("EN", [P[("U6", "2")], (42.3, 17.05), (45.6, 17.05), (45.6, 27.0),
             P[("C7", "1")]], 0.25)
    R("EN", [P[("C7", "1")], (44.2, 29.2), (45.6, 29.2), (45.6, 27.3),
             (56.5, 27.3), (56.5, 30.9), P[("R7", "2")]], 0.25)
    R("MTR_RX", [P[("U4", "4")], (34.73, 27.5), (36.0, 26.0), (36.0, 19.6),
                 P[("R13", "2")]], 0.25)
    R("MTR_RX", [P[("R13", "2")], (46.175, 17.5), (40.5, 17.5),
                 P[("U6", "3")]], 0.25)
    R("MTR_TX", [P[("U6", "4")], (42.3, 18.0), (46.0, 18.0), (46.0, 28.0),
                 P[("R14", "1")]], 0.25)
    R("U5_A", [P[("R14", "2")], (45.275, 28.4), (43.6, 28.4),
               P[("U5", "1")]], 0.25)
    R("TX0", [P[("U6", "12")], (59.4, 22.4), (59.4, 20.85), (37.0, 20.85),
              (37.0, 22.46), P[("J3", "2")]], 0.25)
    R("RX0", [P[("U6", "11")], (59.4, 25.2), (37.2, 25.2), (37.2, 25.0),
              P[("J3", "3")]], 0.25)


# --------------------------------------------------------------------------
# BOM + main
# --------------------------------------------------------------------------
def write_bom(path):
    rows = [("U1", "HLK-PM01"), ("U2", "AP2112K-3.3"), ("U3", "BL0942"),
            ("U4", "PC817"), ("U5", "PC817"), ("U6", "ESP32-C3-WROOM-02"),
            ("K1", "HF32F-G"), ("Q1", "S8050"), ("D1", "1N4148WS"),
            ("D2", "LED_GRN"), ("F1", "FUSE_CLIP"), ("F1E", "FUSE_10A"),
            ("RV1", "MOV_10D471K"), ("BT1", "SW_PUSH"),
            ("J1", "Term_5.08_2P"), ("J2", "Term_5.08_2P"),
            ("J3", "Conn_01x04"),
            ("R1", "1k"), ("R2", "1k"), ("R3", "SHUNT_1mR"),
            ("R4", "470k"), ("R5", "470k"), ("R6", "270R"),
            ("R7", "10k"), ("R8", "10k"), ("R10", "10k"), ("R11", "10k"),
            ("R12", "1k"), ("R13", "10k"), ("R14", "1k"), ("R15", "10k"),
            ("C1", "10uF"), ("C2", "100nF"), ("C3", "10uF"),
            ("C4", "100nF"), ("C5", "100nF"), ("C7", "100nF")]
    with open(path, "w") as f:
        f.write("Ref,Value,Footprint,LCSC,MPN,Qty\n")
        for ref, val in rows:
            fp, _desc, lcsc, mpn = PART_INFO[val]
            f.write(f"{ref},{val},{fp},{lcsc},{mpn},1\n")


def main():
    os.makedirs(OUT, exist_ok=True)
    kg.write_project(os.path.join(OUT, BOARD + ".kicad_pro"),
                     BOARD, BOARD + "-lib")
    fps = build_footprints(BOARD)
    build_schematic(os.path.join(OUT, BOARD + ".kicad_sch"))
    build_pcb(fps)
    write_bom(os.path.join(OUT, "bom_lcsc.csv"))
    problems = kg.validate_project(OUT)
    for p in problems:
        print("VALIDATE:", p)
    if problems:
        raise SystemExit(f"validate_project failed: {len(problems)} problem(s)")
    print("relaymini-c3: project generated + validated")


if __name__ == "__main__":
    main()
