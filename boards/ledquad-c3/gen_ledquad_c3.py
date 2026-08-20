#!/usr/bin/env python3
"""ledquad-c3 -- programmatic KiCad 8 project generator.

50x40 mm 2-layer 4-channel PWM LED-strip driver: ESP32-C3-WROOM-02,
12-24 V in (5.08 mm terminal + 5 A 1206 fuse), AP63205 buck to 5 V,
AP2112K-3.3 LDO, 4x AO3400A low-side MOSFETs, 5-pin output terminal,
USB-C programming with SS34 diode-OR of VBUS vs buck 5 V.

Run:  python3 gen_ledquad_c3.py

ESP32-C3-WROOM-02 custom footprint geometry verified against the official
Espressif KiCad library footprint (pad columns +/-8.75 mm, pitch 1.5 mm,
pads 1.5x0.9 mm, module outline 18.0x20.0 mm, antenna area at pin-1 end):
https://github.com/espressif/kicad-libraries/blob/main/footprints/Espressif.pretty/ESP32-C3-WROOM-02.kicad_mod
and the module datasheet:
https://www.espressif.com/sites/default/files/documentation/esp32-c3-wroom-02_datasheet_en.pdf
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "tools"))
import kicadgen as kg  # noqa: E402

BOARD = "ledquad-c3"
W, H = 50.0, 40.0
OUT = os.path.dirname(os.path.abspath(__file__))

DS = {
    "ESP32-C3-WROOM-02": "https://www.espressif.com/sites/default/files/documentation/esp32-c3-wroom-02_datasheet_en.pdf",
    "USB_C_16P": "https://www.lcsc.com/datasheet/lcsc_datasheet_2410252104_Korean-Hroparts-Elec-TYPE-C-31-M-12_C165948.pdf",
    "AP2112K-3.3": "https://www.diodes.com/assets/Datasheets/AP2112.pdf",
    "AP63205": "https://www.diodes.com/assets/Datasheets/AP63200-AP63201-AP63203-AP63205.pdf",
    "AO3400A": "http://www.aosmd.com/res/data_sheets/AO3400A.pdf",
    "SS34": "https://www.lcsc.com/datasheet/lcsc_datasheet_1810131211_MDD-Microdiode-Electronics--SS34_C8678.pdf",
    "FUSE_5A": "https://www.lcsc.com/datasheet/lcsc_datasheet_2406141455_JDTFUSE-JFC1206-1500FS_C136351.pdf",
    "L_4R7": "https://www.lcsc.com/datasheet/lcsc_datasheet_2304120030_cjiang-Changjiang-Microelectronics-Tech-FNR4030S4R7MT_C167874.pdf",
    "TB_2P": "https://www.lcsc.com/datasheet/lcsc_datasheet_1810231712_Cixi-Kefa-Elec-KF128-5-08-2P-AA_C474952.pdf",
    "TB_5P": "https://www.lcsc.com/datasheet/lcsc_datasheet_2406031720_NINGBO-KANGNING-ELECTRONICS-WJ500V-5-08-05P-14-00A_C42377750.pdf",
    "SW_PUSH": "https://www.lcsc.com/datasheet/lcsc_datasheet_1810251613_SHOU-HAN-TS-1187A-B-A-B_C139797.pdf",
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
                    "C51115", "AP2112K-3.3TRG1"),
    "AP63205": ("Package_TO_SOT_SMD:SOT-23-6",
                "Buck 3.8-32V to 5V 2A (fixed)", "C2071056", "AP63205WU-7"),
    "AO3400A": ("Package_TO_SOT_SMD:SOT-23", "N-MOSFET 30V 5.7A", "C20917",
                "AO3400A"),
    "SS34": ("Diode_SMD:D_SMA", "Schottky 40V 3A SMA", "C8678", "SS34"),
    "FUSE_5A": ("Fuse:Fuse_1206_3216Metric", "Fuse 5A 32V 1206 disposable",
                "C136351", "JFC1206-1500FS"),
    "L_4R7": ("custom:L-4x4-4R7", "Power inductor 4.7uH 3.2A 4x4mm",
              "C167874", "FNR4030S4R7MT"),
    "TB_2P": ("custom:TB-5.08-2P", "Screw terminal 5.08mm 2P", "C474952",
              "KF128-5.08-2P-AA"),
    "TB_5P": ("custom:TB-5.08-5P", "Screw terminal 5.08mm 5P", "C42377750",
              "WJ500V-5.08-05P-14-00A"),
    "10k": ("Resistor_SMD:R_0603_1608Metric", "Resistor 10k 0603", "C25804",
            "0603WAF1002T5E"),
    "100k": ("Resistor_SMD:R_0603_1608Metric", "Resistor 100k 0603", "C25803",
             "0603WAF1003T5E"),
    "100R": ("Resistor_SMD:R_0603_1608Metric", "Resistor 100R 0603 1%",
             "C22369795", "RCA03100RFLF"),
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
    "22uF": ("Capacitor_SMD:C_0805_2012Metric", "Cap MLCC 22uF 0805 25V",
             "C45783", "CL21A226MAQNNNE"),
    "LED_RED": ("LED_SMD:LED_0603_1608Metric", "LED red 0603", "C2286",
                "LTST-C190KRKT"),
    "LED_GRN": ("LED_SMD:LED_0603_1608Metric", "LED green 0603", "C2297",
                "LTST-C190KGKT"),
    "SW_PUSH": ("custom:Tactile-6x6-SMD", "Tactile switch 6x6 SMD", "C139797",
                "TS-1187A-B-A-B"),
    "Conn_01x04": ("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
                   "Header 1x4 (prog)", "C49258", "KH-2.54PH180-1X4P-L13.5"),
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

    # --- Power inductor 4x4 mm (FNR4030S4R7MT): 2 SMD pads -----------------
    fp = kg.Footprint(lib_prefix, "L-4x4-4R7")
    fp.add_pad("1", "smd", "rect", -1.45, 0, 1.5, 3.4)
    fp.add_pad("2", "smd", "rect", 1.45, 0, 1.5, 3.4)
    fp.add_rect(-2.0, -2.0, 2.0, 2.0, "F.Fab", 0.1)
    fp.add_rect(-2.5, -2.25, 2.5, 2.25, "F.CrtYd", 0.05)
    fp.add_line(-2.0, -2.1, 2.0, -2.1, "F.SilkS")
    fp.add_line(-2.0, 2.1, 2.0, 2.1, "F.SilkS")
    fps["L-4x4-4R7"] = fp

    # --- Screw terminal 5.08 mm 2P (KF128-5.08-2P) --------------------------
    fp = kg.Footprint(lib_prefix, "TB-5.08-2P")
    for i in range(2):
        fp.add_pad(str(i + 1), "thru_hole", "rect" if i == 0 else "circle",
                   i * 5.08, 0, 2.2, 2.2, layers=("*.Cu", "*.Mask"), drill=1.3)
    fp.add_rect(-2.6, -4.0, 2 * 5.08 - 2.54 + 0.06, 4.0, "F.Fab", 0.1)
    fp.add_rect(-1.5, -3.4, 2 * 5.08 - 2.54 + 0.06, 3.4, "F.CrtYd", 0.05)
    fp.add_rect(-2.6, -4.0, 2 * 5.08 - 2.54 + 0.06, 4.0, "F.SilkS", 0.12)
    fp.add_text("+", -1.27, -2.6, "F.SilkS", 1.0)
    fps["TB-5.08-2P"] = fp

    # --- Screw terminal 5.08 mm 5P (WJ500V-5.08-05P) ------------------------
    fp = kg.Footprint(lib_prefix, "TB-5.08-5P")
    for i in range(5):
        fp.add_pad(str(i + 1), "thru_hole", "rect" if i == 0 else "circle",
                   i * 5.08, 0, 2.2, 2.2, layers=("*.Cu", "*.Mask"), drill=1.3)
    fp.add_rect(-2.6, -4.0, 5 * 5.08 - 2.54 + 0.06, 4.0, "F.Fab", 0.1)
    fp.add_rect(-2.6, -3.4, 22.0, 3.4, "F.CrtYd", 0.05)
    fp.add_rect(-2.6, -4.0, 5 * 5.08 - 2.54 + 0.06, 4.0, "F.SilkS", 0.12)
    fp.add_text("+", -1.27, -2.6, "F.SilkS", 1.0)
    fps["TB-5.08-5P"] = fp

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
# ESP32-C3-WROOM-02 pins: 1=3V3 2=EN 3=IO4 4=IO5 5=IO6 6=IO7 7=IO8 8=IO9
# 9=GND 10=IO10 11=RXD0/IO20 12=TXD0/IO21 13=IO18/USB-DN 14=IO19/USB-DP
# 15=IO3 16=IO2 17=IO1 18=IO0 19=EP(GND)
U1_PLAN = {"1": "+3V3", "2": "EN", "3": "PWM_R", "4": "PWM_G", "5": "PWM_B",
           "6": "PWM_W", "7": None, "8": "BOOT", "9": "GND", "10": "STAT_LED",
           "11": "RX0", "12": "TX0", "13": "USB_DM", "14": "USB_DP",
           "15": None, "16": None, "17": None, "18": None, "19": "GND"}
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
# AP63205 (TSOT-23-6): 1=FB 2=EN 3=VIN 4=GND 5=SW 6=BST
U2_PLAN = {"1": "5V_BUCK", "2": "VIN_EN", "3": "VIN", "4": "GND",
           "5": "SW", "6": "BST"}
U3_PLAN = {"1": "+5V", "2": "GND", "3": "+5V", "4": None, "5": "+3V3"}
# AO3400A SOT-23: 1=G 2=S 3=D
Q_PLAN = {"Q1": {"1": "GATE_R", "2": "GND", "3": "OUT_R"},
          "Q2": {"1": "GATE_G", "2": "GND", "3": "OUT_G"},
          "Q3": {"1": "GATE_B", "2": "GND", "3": "OUT_B"},
          "Q4": {"1": "GATE_W", "2": "GND", "3": "OUT_W"}}
RX_PLAN = {"R1": {"1": "5V_BUCK", "2": "GATE_R"},   # gate series 100R
           "R2": {"1": "5V_BUCK", "2": "GATE_G"},
           "R3": {"1": "5V_BUCK", "2": "GATE_B"},
           "R4": {"1": "5V_BUCK", "2": "GATE_W"},
           "R5": {"1": "GATE_R", "2": "GND"},        # gate pulldowns 10k
           "R6": {"1": "GATE_G", "2": "GND"},
           "R7": {"1": "GATE_B", "2": "GND"},
           "R8": {"1": "GATE_W", "2": "GND"},
           "R9": {"1": "PWM_R", "2": "5V_BUCK"},     # placeholder; fixed below
           }
# NOTE on gate wiring: PWM_x --R(100R)--> GATE_x --R(10k)--> GND.
# R1..R4 pad1 must see PWM_x, not 5V_BUCK; patched here after table def.
RX_PLAN["R1"] = {"1": "PWM_R", "2": "GATE_R"}
RX_PLAN["R2"] = {"1": "PWM_G", "2": "GATE_G"}
RX_PLAN["R3"] = {"1": "PWM_B", "2": "GATE_B"}
RX_PLAN["R4"] = {"1": "PWM_W", "2": "GATE_W"}
del RX_PLAN["R9"]
RX_PLAN.update({
    "R9": {"1": "USB_CC1", "2": "GND"},     # CC1 5.1k
    "R10": {"1": "USB_CC2", "2": "GND"},    # CC2 5.1k
    "R11": {"1": "USB_DP_CON", "2": "USB_DP"},  # 22R series
    "R12": {"1": "USB_DM_CON", "2": "USB_DM"},  # 22R series
    "R13": {"1": "+3V3", "2": "EN"},        # EN pull-up 10k
    "R14": {"1": "+3V3", "2": "LED2_A"},    # status LED R 1k
    "R15": {"1": "+5V", "2": "LED1_A"},     # power LED R 1k
    "R16": {"1": "VIN", "2": "VIN_EN"},     # buck EN pull-up 100k
})
CX_PLAN = {"C1": {"1": "VIN", "2": "GND"},      # buck input bulk 10uF
           "C2": {"1": "VIN", "2": "GND"},      # buck input HF 100nF
           "C3": {"1": "BST", "2": "SW"},       # bootstrap 100nF
           "C4": {"1": "5V_BUCK", "2": "GND"},  # buck output 22uF
           "C5": {"1": "5V_BUCK", "2": "GND"},  # buck output 22uF
           "C6": {"1": "+5V", "2": "GND"},      # LDO input 10uF
           "C7": {"1": "+3V3", "2": "GND"},     # LDO output 10uF
           "C8": {"1": "+3V3", "2": "GND"},     # module decouple 100nF
           "C9": {"1": "EN", "2": "GND"},       # EN cap 100nF
           "C10": {"1": "VBUS", "2": "GND"},    # USB VBUS cap 10uF
           }
DX_PLAN = {"D1": {"1": "LED1_A", "2": "GND"},        # red power LED
           "D2": {"1": "LED2_A", "2": "STAT_LED"},   # green status (act. low)
           "D3": {"1": "VBUS", "2": "+5V"},          # SS34 OR: USB side
           "D4": {"1": "5V_BUCK", "2": "+5V"}}       # SS34 OR: buck side
F_PLAN = {"F1": {"1": "VIN_RAW", "2": "VIN"}}
L_PLAN = {"L1": {"1": "SW", "2": "5V_BUCK"}}
BT_PLAN = {"BT1": {"1": "EN", "2": "GND", "3": "EN", "4": "GND"},
           "BT2": {"1": "BOOT", "2": "GND", "3": "BOOT", "4": "GND"}}
J_PLAN = {"J1": {"1": "VIN_RAW", "2": "GND"},
          "J2": {"1": "VIN", "2": "OUT_R", "3": "OUT_G", "4": "OUT_B",
                 "5": "OUT_W"},
          "J3": {"1": "+3V3", "2": "TX0", "3": "RX0", "4": "GND"}}


def _resolve(sch, ref, plan):
    for num, net in plan.items():
        pt = sch.pin_at(ref, num)
        if net is None:
            sch.no_connect(round(pt[0], 2), round(pt[1], 2))
        else:
            sch.label(net, round(pt[0], 2), round(pt[1], 2))


def build_schematic(path, sym_path=None):
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
                           datasheet=DS.get(value_key, "~"), lcsc=info[2])

    # module: 1..9 left, 10..18 right, 19 (EP) bottom
    nums = [str(i) for i in range(1, 10)] + [str(i) for i in range(10, 19)]
    pins = [(n, U1_NAMES[n], "passive", "left" if i < 9 else "right")
            for i, n in enumerate(nums)]
    pins.append(("19", "EP", "passive", "bottom"))
    lib.add_box_symbol("ESP32-C3-WROOM-02", "U", pins,
                       footprint=BOARD + ":ESP32-C3-WROOM-02",
                       datasheet=DS["ESP32-C3-WROOM-02"],
                       lcsc=PART_INFO["ESP32-C3-WROOM-02"][2])

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

    box("AP63205", "U", ["1", "2", "3", "4", "5", "6"],
        {"1": "FB", "2": "EN", "3": "VIN", "4": "GND", "5": "SW", "6": "BST"},
        "AP63205")
    box("AP2112K-3.3", "U", ["1", "2", "3", "4", "5"],
        {"1": "VIN", "2": "GND", "3": "EN", "4": "NC", "5": "VOUT"},
        "AP2112K-3.3")
    box("AO3400A", "Q", ["1", "2", "3"],
        {"1": "G", "2": "S", "3": "D"}, "AO3400A")
    box("SS34", "D", ["1", "2"], {"1": "A", "2": "K"}, "SS34")
    box("FUSE_5A", "F", ["1", "2"], {"1": "1", "2": "2"}, "FUSE_5A")
    box("L_4R7", "L", ["1", "2"], {"1": "1", "2": "2"}, "L_4R7")
    box("TB_2P", "J", ["1", "2"], {"1": "1", "2": "2"}, "TB_2P")
    box("TB_5P", "J", ["1", "2", "3", "4", "5"],
        {"1": "1", "2": "2", "3": "3", "4": "4", "5": "5"}, "TB_5P")
    for val in ("10k", "100k", "100R", "5.1k", "22R", "1k"):
        box(val, "R", ["1", "2"], {"1": "1", "2": "2"}, val)
    for val in ("100nF", "10uF", "22uF"):
        box(val, "C", ["1", "2"], {"1": "1", "2": "2"}, val)
    for val in ("LED_RED", "LED_GRN"):
        box(val, "D", ["1", "2"], {"1": "A", "2": "K"}, val)
    box("SW_PUSH", "BT", ["1", "2", "3", "4"],
        {"1": "A1", "2": "A2", "3": "B1", "4": "B2"}, "SW_PUSH")
    box("Conn_01x04", "J", ["1", "2", "3", "4"],
        {"1": "1", "2": "2", "3": "3", "4": "4"}, "Conn_01x04")

    placements = [
        ("ESP32-C3-WROOM-02", "U1", 100, 70, U1_PLAN),
        ("USB_C_16P", "X1", 190, 70, X1_PLAN),
        ("AP63205", "U2", 40, 120, U2_PLAN),
        ("AP2112K-3.3", "U3", 40, 160, U3_PLAN),
        ("L_4R7", "L1", 70, 120, L_PLAN["L1"]),
        ("FUSE_5A", "F1", 15, 120, F_PLAN["F1"]),
        ("SS34", "D3", 70, 160, DX_PLAN["D3"]),
        ("SS34", "D4", 90, 160, DX_PLAN["D4"]),
        ("LED_RED", "D1", 110, 160, DX_PLAN["D1"]),
        ("LED_GRN", "D2", 130, 160, DX_PLAN["D2"]),
        ("TB_2P", "J1", 15, 70, J_PLAN["J1"]),
        ("TB_5P", "J2", 260, 70, J_PLAN["J2"]),
        ("Conn_01x04", "J3", 300, 120, J_PLAN["J3"]),
        ("SW_PUSH", "BT1", 300, 160, BT_PLAN["BT1"]),
        ("SW_PUSH", "BT2", 300, 200, BT_PLAN["BT2"]),
    ]
    for sym, ref, x, y, plan in placements:
        sch.place(sym, ref, x, y, value=sym)
        _resolve(sch, ref, plan)
    rvals = [("R1", "100R"), ("R2", "100R"), ("R3", "100R"), ("R4", "100R"),
             ("R5", "10k"), ("R6", "10k"), ("R7", "10k"), ("R8", "10k"),
             ("R9", "5.1k"), ("R10", "5.1k"), ("R11", "22R"), ("R12", "22R"),
             ("R13", "10k"), ("R14", "1k"), ("R15", "1k"), ("R16", "100k")]
    for ref, val in rvals:
        n = int(ref[1:])
        sch.place(val, ref, 150 + (n % 4) * 25, 105 + (n // 4) * 12, value=val)
        _resolve(sch, ref, RX_PLAN[ref])
    for i, (ref, val) in enumerate(
            [("C1", "10uF"), ("C2", "100nF"), ("C3", "100nF"), ("C4", "22uF"),
             ("C5", "22uF"), ("C6", "10uF"), ("C7", "10uF"), ("C8", "100nF"),
             ("C9", "100nF"), ("C10", "10uF")]):
        sch.place(val, ref, 230 + (i % 5) * 25, 105 + (i // 5) * 12, value=val)
        _resolve(sch, ref, CX_PLAN[ref])
    for ref in ("Q1", "Q2", "Q3", "Q4"):
        sch.place("AO3400A", ref, 260 + 18 * int(ref[1:]), 190,
                  value="AO3400A")
        _resolve(sch, ref, Q_PLAN[ref])

    for i, name in enumerate(("GND", "GND", "+3V3", "+5V", "VBUS", "+5V")):
        x, y = 20 + 10 * i, 25
        sch.place_power(name, x, y)
        sch.label(name, x, y)

    sch.sheet_note("ledquad-c3: 4-ch PWM LED driver, 12-24V in, ESP32-C3. "
                   "Buck: AP63205 (fixed 5V/2A), VBUS/5V diode-OR via SS34.")
    lib.save(os.path.join(OUT, BOARD + "-lib.kicad_sym"))
    sch.save(path)

# --------------------------------------------------------------------------
# PCB: geometric copper model + self-check (0.15 mm clearance)
# --------------------------------------------------------------------------
CLEAR = 0.15       # min copper-to-copper clearance (mm)
EDGE_CLEAR = 0.4   # min copper-to-board-edge distance (mm)
CRTYD = 1.0        # max courtyard overlap area (mm^2)
VIA_R = 0.4        # via radius (0.8 dia / 0.4 drill)
KEEPOUT = (16.5, 0.0, 37.5, 7.0)  # antenna keepout (x0, y0, x1, y1)


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
    return min(_seg_seg_dist((x1, y1), (x2, y2), corners[i], corners[(i + 1) % 4])
               for i in range(4))


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
# PCB build: placement + hand-routed, self-checked copper
# --------------------------------------------------------------------------
def path_pcb():
    return os.path.join(OUT, BOARD + ".kicad_pcb")


def build_pcb(fps):
    b = PcbBuilder(BOARD)
    pcb = b.pcb
    pcb.add_mounting_holes()

    STD = {
        "0603": "Resistor_SMD:R_0603_1608Metric",
        "0805": "Capacitor_SMD:C_0805_2012Metric",
        "FUSE": "Fuse:Fuse_1206_3216Metric",
        "SMA": "Diode_SMD:D_SMA",
        "SOT23": "Package_TO_SOT_SMD:SOT-23",
        "SOT235": "Package_TO_SOT_SMD:SOT-23-5",
        "SOT236": "Package_TO_SOT_SMD:SOT-23-6",
        "USBC": "Connector_USB:USB_C_Receptacle_USB2.0_16P",
        "HDR4": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
    }
    PL = [
        (fps["ESP32-C3-WROOM-02"], "U1", "ESP32-C3-WROOM-02", 27.0, 14.0, 0),
        (STD["USBC"], "X1", "USB_C_16P", 41.0, 34.0, 0),
        (fps["TB-5.08-2P"], "J1", "TB_2P", 2.7, 33.0, 0),
        (fps["TB-5.08-5P"], "J2", "TB_5P", 13.0, 35.0, 0),
        (STD["HDR4"], "J3", "Conn_01x04", 47.0, 7.0, 0),
        (STD["SOT236"], "U2", "AP63205", 37.3, 25.0, 0),
        (STD["SOT235"], "U3", "AP2112K-3.3", 38.8, 14.0, 0),
        (fps["L-4x4-4R7"], "L1", "L_4R7", 41.2, 25.0, 0),
        (STD["FUSE"], "F1", "FUSE_5A", 31.6, 28.0, 0),
        (STD["SMA"], "D3", "SS34", 44.0, 17.0, 90),
        (STD["SMA"], "D4", "SS34", 47.0, 18.5, 90),
        ("LED_SMD:LED_0603_1608Metric", "D1", "LED_RED", 42.5, 8.0, 0),
        ("LED_SMD:LED_0603_1608Metric", "D2", "LED_GRN", 42.5, 10.6, 0),
        (STD["SOT23"], "Q1", "AO3400A", 14.0, 29.0, 0),
        (STD["SOT23"], "Q2", "AO3400A", 18.0, 29.0, 0),
        (STD["SOT23"], "Q3", "AO3400A", 22.0, 29.0, 0),
        (STD["SOT23"], "Q4", "AO3400A", 26.0, 29.0, 0),
        (fps["Tactile-6x6-SMD"], "BT1", "SW_PUSH", 8.0, 8.6, 0),
        (fps["Tactile-6x6-SMD"], "BT2", "SW_PUSH", 8.0, 15.0, 0),
        (STD["0603"], "R1", "100R", 10.8, 26.8, 0),
        (STD["0603"], "R2", "100R", 15.0, 26.8, 0),
        (STD["0603"], "R3", "100R", 19.2, 26.8, 0),
        (STD["0603"], "R4", "100R", 23.4, 26.8, 0),
        (STD["0603"], "R5", "10k", 13.0, 31.0, 0),
        (STD["0603"], "R6", "10k", 17.0, 31.0, 0),
        (STD["0603"], "R7", "10k", 21.0, 31.0, 0),
        (STD["0603"], "R8", "10k", 25.0, 31.0, 0),
        (STD["0603"], "R9", "5.1k", 39.0, 31.5, 90),
        (STD["0603"], "R10", "5.1k", 41.0, 31.5, 90),
        (STD["0603"], "R11", "22R", 37.0, 31.5, 90),
        (STD["0603"], "R12", "22R", 35.0, 31.5, 90),
        (STD["0603"], "R13", "10k", 15.3, 9.6, 0),
        (STD["0603"], "R14", "1k", 40.0, 10.6, 0),
        (STD["0603"], "R15", "1k", 40.0, 8.0, 0),
        (STD["0603"], "R16", "100k", 39.5, 27.5, 0),
        (STD["0603"], "C1", "10uF", 33.5, 24.5, 90),
        (STD["0603"], "C2", "100nF", 35.0, 26.6, 90),
        (STD["0603"], "C3", "100nF", 40.5, 21.0, 90),
        (STD["0805"], "C4", "22uF", 44.3, 23.0, 90),
        (STD["0805"], "C5", "22uF", 46.4, 24.0, 90),
        (STD["0603"], "C6", "10uF", 37.4, 10.8, 90),
        (STD["0603"], "C7", "10uF", 41.8, 14.4, 90),
        (STD["0603"], "C8", "100nF", 20.6, 8.1, 180),
        (STD["0603"], "C9", "100nF", 15.0, 14.2, 0),
        (STD["0603"], "C10", "10uF", 43.4, 30.0, 90),
    ]
    for fp, ref, val, x, y, rot in PL:
        b.place(fp, ref, val, x, y, rot)

    def fid(ref, x, y):
        """Assembly fiducial, 1 mm Cu dot + mask opening (FD-001)."""
        fp = kg.Footprint(BOARD, "Fiducial_1mm")
        fp.add_pad("1", "smd", "circle", 0.0, 0.0, 1.0, 1.0,
                   layers=("F.Cu", "F.Mask"))
        fp.add_circle(0, 0, 1.5, "F.CrtYd", 0.05)
        b.place(fp, ref, "Fiducial", x, y)

    fid("H5", 11.0, 2.5)
    fid("H6", 38.5, 2.5)
    fid("H7", 2.5, 20.0)

    ALL_PLANS = {}
    for d in ({"U1": U1_PLAN, "X1": X1_PLAN, "U2": U2_PLAN, "U3": U3_PLAN},
              Q_PLAN, RX_PLAN, CX_PLAN, DX_PLAN, F_PLAN, L_PLAN, BT_PLAN,
              J_PLAN):
        ALL_PLANS.update(d)
    nets = {}
    for ref, plan in ALL_PLANS.items():
        for num, net in plan.items():
            nets[(ref, num)] = net
            b.net_pad(ref, num, net)
    b.collect_pads(nets)

    R = b.route
    V = b.via

    # ===== VIN_RAW: J1.1 -> F1.1 (F.Cu left edge) =====
    R("VIN_RAW", [(2.4, 33.0), (2.4, 24.6), (29.0, 24.6), (29.0, 28.0),
                  (30.15, 28.0)], 0.5)

    # ===== VIN: F1.2 -> U2.3 / C1 / C2 / R16 / J2.1 =====
    R("VIN", [(33.05, 28.0), (38.725, 28.0)], 0.5)
    R("VIN", [(36.5, 28.0), (36.5, 25.95), (35.55, 25.95)], 0.5)
    R("VIN", [(38.725, 28.0), (38.725, 27.5)], 0.5)          # R16.1
    R("VIN", [(33.5, 28.0), (33.5, 27.6)], 0.5)
    V("VIN", 33.5, 27.6)
    R("VIN", [(33.5, 27.6), (33.5, 22.9), (34.4, 22.9), (34.4, 24.3)],
      0.5, "B.Cu")
    V("VIN", 33.5, 22.9)
    R("VIN", [(33.5, 22.9), (33.5, 23.725)], 0.5)             # C1.1
    V("VIN", 34.4, 24.3)
    R("VIN", [(34.4, 24.3), (34.4, 25.825), (35.0, 25.825)], 0.5)  # C2.1
    R("VIN", [(35.2, 28.0), (35.2, 27.7)], 0.5)
    V("VIN", 35.2, 27.7)
    R("VIN", [(35.2, 27.7), (35.2, 32.5), (13.0, 32.5)], 0.5, "B.Cu")
    V("VIN", 13.0, 32.5)
    R("VIN", [(13.0, 32.5), (13.0, 35.0)], 0.5)               # J2.1

    # ===== VIN_EN: R16.2 -> U2.2 =====
    R("VIN_EN", [(40.275, 27.5), (40.275, 29.5), (34.0, 29.5),
                 (34.0, 25.0), (36.35, 25.0)])

    # ===== SW: U2.5 -> L1.1, C3.2 ; BST: U2.6 -> C3.1 =====
    R("SW", [(38.25, 25.0), (39.55, 25.0)], 0.5)
    R("SW", [(40.5, 21.775), (41.0, 21.775), (41.0, 24.0), (40.3, 24.0)], 0.5)
    R("BST", [(38.25, 24.05), (38.25, 21.0), (39.8, 21.0),
              (39.8, 20.225), (40.5, 20.225)])

    # ===== 5V_BUCK: L1.2 -> C4/C5/D4.1 ; U2.1(FB) via B.Cu =====
    R("5V_BUCK", [(42.45, 25.0), (42.45, 22.05), (44.3, 22.05)], 0.5)
    R("5V_BUCK", [(44.3, 22.05), (46.4, 22.05), (46.4, 22.65)], 0.5)
    R("5V_BUCK", [(46.4, 22.35), (48.7, 22.35), (48.7, 16.45),
                  (47.95, 16.45)], 0.5)
    R("5V_BUCK", [(46.4, 22.05), (46.4, 22.35)], 0.5)
    R("5V_BUCK", [(36.35, 24.05), (36.35, 22.3)], 0.5)
    V("5V_BUCK", 36.35, 22.3)
    R("5V_BUCK", [(36.35, 22.3), (41.8, 22.3)], 0.5, "B.Cu")
    V("5V_BUCK", 41.8, 22.3)
    R("5V_BUCK", [(41.8, 22.3), (42.45, 22.3)], 0.5)

    # ===== +5V: D4.2/D3.2 -> U3 / C6 / R15 =====
    R("+5V", [(44.0, 19.05), (44.0, 20.55), (47.0, 20.55)], 0.5)
    R("+5V", [(44.0, 19.05), (44.0, 16.8), (36.8, 16.8), (36.8, 14.95),
              (37.85, 14.95)], 0.5)
    R("+5V", [(37.85, 13.05), (38.3, 13.05), (38.3, 10.025),
              (37.4, 10.025)], 0.5)
    R("+5V", [(44.0, 16.8), (45.5, 16.8), (45.5, 5.6), (39.225, 5.6),
              (39.225, 8.0)], 0.5)

    # ===== +3V3 =====
    R("+3V3", [(39.75, 13.05), (39.75, 9.6), (44.5, 9.6), (44.5, 8.2),
               (47.0, 8.2), (47.0, 7.0)], 0.5)
    R("+3V3", [(39.75, 10.6), (39.225, 10.6)], 0.5)           # R14.1
    R("+3V3", [(39.75, 13.05), (41.8, 13.05), (41.8, 13.625)], 0.5)  # C7.1
    V("+3V3", 44.5, 9.0)
    R("+3V3", [(44.5, 9.0), (44.5, 8.6), (14.3, 8.6)], 0.5, "B.Cu")
    V("+3V3", 14.3, 8.6)
    R("+3V3", [(14.3, 8.6), (14.3, 9.6), (14.525, 9.6)], 0.5)  # R13.1
    R("+3V3", [(18.25, 8.1), (18.25, 7.8)], 0.5)              # U1.1
    V("+3V3", 18.25, 7.8)
    R("+3V3", [(18.25, 7.8), (22.4, 7.8), (22.4, 8.6)], 0.5, "B.Cu")
    V("+3V3", 22.4, 8.1)
    R("+3V3", [(22.4, 8.1), (21.375, 8.1)], 0.5)              # C8.1

    # ===== USB-C: VBUS + CC + data =====
    # VBUS pads 2/7/10 escape downward (0.25 stubs, joined on trunk);
    # pad 15 (44.25) is shell-blocked -> bonded inside connector (README).
    for vx in (37.75, 40.25, 41.75):
        R("VBUS", [(vx, 36.6), (vx, 38.0)], 0.25)
        R("VBUS", [(vx, 38.0), (vx, 38.9)], 0.25)
    R("VBUS", [(37.75, 38.9), (47.0, 38.9)], 0.5)
    R("VBUS", [(47.0, 38.9), (47.0, 29.6), (43.4, 29.6), (43.4, 29.225)], 0.5)
    V("VBUS", 47.0, 38.9)
    R("VBUS", [(47.0, 38.9), (49.0, 38.9), (49.0, 13.0)], 0.5, "B.Cu")
    V("VBUS", 49.0, 13.0)
    R("VBUS", [(49.0, 13.0), (44.5, 13.0), (44.5, 14.5)], 0.5)  # D3.1
    R("USB_DP_CON", [(38.75, 36.6), (38.75, 34.8), (35.9, 34.8),
                     (35.9, 30.725), (37.0, 30.725)])
    R("USB_DM_CON", [(39.25, 36.6), (39.25, 35.3), (33.9, 35.3),
                     (33.9, 30.725), (35.0, 30.725)])
    R("USB_CC1", [(38.25, 36.6), (38.25, 34.4), (40.1, 34.4),
                  (40.1, 30.725), (39.0, 30.725)])
    R("USB_CC2", [(43.75, 36.6), (43.75, 35.3), (42.1, 35.3),
                  (42.1, 30.725), (41.0, 30.725)])
    # module side data (B.Cu lanes)
    R("USB_DP", [(35.75, 14.1), (36.1, 14.1)], 0.25)
    V("USB_DP", 36.1, 14.1)
    R("USB_DP", [(36.1, 14.1), (36.15, 14.1), (36.15, 32.9), (37.6, 32.9)],
      0.25, "B.Cu")
    V("USB_DP", 37.6, 32.9)
    R("USB_DP", [(37.6, 32.9), (37.6, 32.275), (37.0, 32.275)], 0.25)
    R("USB_DM", [(35.75, 15.6), (35.9, 15.6), (35.9, 17.0), (37.4, 17.0)],
      0.25)
    V("USB_DM", 37.4, 17.0)
    R("USB_DM", [(37.4, 17.0), (37.4, 33.2), (35.7, 33.2)], 0.25, "B.Cu")
    V("USB_DM", 35.7, 33.2)
    R("USB_DM", [(35.7, 33.2), (35.0, 33.2), (35.0, 32.275)], 0.25)

    # ===== UART: U1.12/11 -> J3.2/3 (B.Cu) =====
    R("TX0", [(35.75, 17.1), (39.4, 17.1)], 0.25)
    V("TX0", 39.4, 17.1)
    R("TX0", [(39.4, 17.1), (47.8, 17.1), (47.8, 9.54)], 0.25, "B.Cu")
    V("TX0", 47.8, 9.54)
    R("TX0", [(47.8, 9.54), (47.0, 9.54)], 0.25)
    R("RX0", [(35.75, 18.6), (39.4, 18.6)], 0.25)
    V("RX0", 39.4, 18.6)
    R("RX0", [(39.4, 18.6), (48.4, 18.6), (48.4, 12.08)], 0.25, "B.Cu")
    V("RX0", 48.4, 12.08)
    R("RX0", [(48.4, 12.08), (47.0, 12.08)], 0.25)

    # ===== STAT_LED: U1.10 -> D2.2 =====
    R("STAT_LED", [(35.75, 20.1), (35.4, 20.1), (35.4, 21.2)], 0.25)
    V("STAT_LED", 35.4, 21.2)
    R("STAT_LED", [(35.4, 21.2), (42.6, 21.2), (42.6, 22.7)], 0.25, "B.Cu")
    V("STAT_LED", 42.6, 22.7)
    R("STAT_LED", [(42.6, 22.7), (42.6, 10.6), (43.275, 10.6)], 0.25)

    # ===== LED anode nets =====
    R("LED1_A", [(40.775, 8.0), (41.725, 8.0)])
    R("LED2_A", [(40.775, 10.6), (41.725, 10.6)])

    # ===== EN / BOOT =====
    R("EN", [(18.25, 9.6), (16.075, 9.6)])
    R("EN", [(16.075, 9.6), (15.4, 9.6), (15.4, 12.0), (14.225, 12.0),
             (14.225, 14.2)])
    V("EN", 15.0, 12.0)
    R("EN", [(15.0, 12.0), (15.0, 9.4), (1.8, 9.4), (1.8, 10.85)],
      0.25, "B.Cu")
    V("EN", 1.8, 10.85)
    R("EN", [(1.8, 10.85), (3.5, 10.85)])
    R("EN", [(3.5, 10.85), (3.5, 6.35)])
    R("BOOT", [(18.25, 18.6), (15.2, 18.6)], 0.25)
    V("BOOT", 15.2, 18.6)
    R("BOOT", [(15.2, 18.6), (15.2, 26.8), (2.5, 26.8), (2.5, 17.25)],
      0.25, "B.Cu")
    V("BOOT", 2.5, 17.25)
    R("BOOT", [(2.5, 17.25), (3.5, 17.25)])
    R("BOOT", [(3.5, 17.25), (3.5, 12.75)])

    # ===== PWM channels (B.Cu lanes down the left side) =====
    pwm = [
        ("PWM_R", 11.1, 15.9, 25.6, [(15.9, 25.6), (10.025, 25.6),
                                     (10.025, 26.8)]),
        ("PWM_G", 12.6, 16.6, 26.2, [(16.7, 26.2), (16.7, 26.0),
                                     (14.225, 26.0), (14.225, 26.8)],
         [(16.6, 26.2), (16.7, 26.2)]),
        ("PWM_B", 14.1, 17.3, 26.9, [(17.4, 26.9), (18.025, 26.9),
                                     (18.025, 26.8)],
         [(17.3, 26.9), (17.4, 26.9)]),
        ("PWM_W", 15.6, 18.0, 27.8, [(18.1, 27.8), (22.625, 27.8),
                                     (22.625, 26.8)],
         [(18.0, 27.8), (18.1, 27.8)]),
    ]
    for item in pwm:
        net, py, lx, vy, tail = item[:5]
        xlink = item[5] if len(item) > 5 else None
        R(net, [(18.25, py), (lx, py)], 0.25)
        V(net, lx, py)
        R(net, [(lx, py), (lx, vy)], 0.25, "B.Cu")
        if xlink:
            R(net, xlink, 0.25, "B.Cu")
            V(net, xlink[-1][0], xlink[-1][1])
        else:
            V(net, lx, vy)
        R(net, tail, 0.25)
    # gate series R -> Q gate
    R("GATE_R", [(11.575, 26.8), (11.575, 28.525), (13.05, 28.525)])
    R("GATE_G", [(15.775, 26.8), (15.775, 28.525), (17.05, 28.525)])
    R("GATE_B", [(19.975, 26.8), (19.975, 28.525), (21.05, 28.525)])
    R("GATE_W", [(24.175, 26.8), (24.175, 28.525), (25.05, 28.525)])
    # gate pulldowns
    R("GATE_R", [(11.575, 28.525), (11.575, 31.0), (12.225, 31.0)])
    R("GATE_G", [(15.775, 28.525), (15.775, 31.0), (16.225, 31.0)])
    R("GATE_B", [(19.975, 28.525), (19.975, 31.0), (20.225, 31.0)])
    R("GATE_W", [(24.175, 28.525), (24.175, 31.0), (24.225, 31.0)])

    # ===== outputs: Q drains -> J2 =====
    R("OUT_R", [(14.95, 29.0), (14.95, 32.6), (17.08, 32.6), (17.08, 34.0)],
      0.5)
    R("OUT_G", [(18.95, 29.0), (18.95, 32.0), (22.16, 32.0), (22.16, 34.0)],
      0.5)
    R("OUT_B", [(22.95, 29.0), (22.95, 32.6), (27.24, 32.6), (27.24, 34.0)],
      0.5)
    R("OUT_W", [(26.95, 29.0), (26.95, 30.2), (27.8, 30.2), (27.8, 31.6),
                (33.32, 31.6), (33.32, 35.0)], 0.5)

    # ===== GND: stubs + vias to B.Cu pour =====
    gnd_vias = [
        ("U1", "9", 18.25, 21.5),
        ("U2", "4", 37.45, 27.0),
        ("C1", "2", 32.3, 26.2),
        ("C2", "2", 34.8, 27.375),
        ("C4", "2", 44.3, 25.2),
        ("C5", "2", 46.4, 25.2),
        ("C6", "2", 37.2, 11.6),
        ("C7", "2", 42.5, 15.4),
        ("C9", "2", 15.2, 14.2),
        ("C10", "2", 44.0, 32.0),
        ("D1", "2", 43.6, 8.7),
        ("J1", "2", 9.08, 31.6),
        ("J3", "4", 45.5, 17.0),
        ("Q1", "2", 13.3, 31.5),
        ("Q2", "2", 17.3, 31.5),
        ("Q3", "2", 21.3, 31.5),
        ("Q4", "2", 25.3, 31.5),
        ("R5", "2", 14.6, 31.6),
        ("R6", "2", 16.9, 31.5),
        ("R8", "2", 25.2, 31.7),
        ("R9", "2", 39.0, 33.6),
        ("R10", "2", 41.0, 33.6),
        ("BT1", "2", 14.2, 6.35),
        ("BT1", "4", 11.0, 10.85),
        ("BT2", "2", 11.0, 12.75),
        ("BT2", "4", 11.0, 17.25),
    ]
    for ref, num, vx, vy in gnd_vias:
        px, py = b.pad_xy[(ref, num)]
        if abs(px - vx) > 0.01 and abs(py - vy) > 0.01:
            R("GND", [(px, py), (vx, py), (vx, vy)], 0.5)
        elif abs(px - vx) > 0.01 or abs(py - vy) > 0.01:
            R("GND", [(px, py), (vx, vy)], 0.5)
        V("GND", vx, vy)
    # special GND ties (narrow stubs)
    R("GND", [(37.85, 14.0), (36.7, 14.0)], 0.25)            # U3.2
    R("GND", [(36.7, 14.0), (36.7, 15.2)], 0.25)
    R("GND", [(36.7, 15.2), (36.7, 16.3)], 0.25)
    V("GND", 36.7, 16.3)
    R("GND", [(19.825, 8.1), (20.6, 8.1)], 0.25)             # C8.2
    R("GND", [(20.6, 8.1), (20.6, 9.4)], 0.25)
    V("GND", 20.6, 9.4)
    # R7 pulldown GND ties into Q3 via
    R("GND", [(21.775, 31.0), (21.3, 31.0), (21.3, 31.5)], 0.5)
    # module exposed pad: vias-in-pad
    V("GND", 27.4, 13.8)
    V("GND", 28.5, 15.0)
    # USB-C GND pads + shell (p16 via; p15/VBUS shell-blocked, see README)
    R("GND", [(37.25, 36.6), (36.9, 36.6), (36.9, 37.5)], 0.25)
    V("GND", 36.9, 37.5)
    R("GND", [(40.75, 36.6), (41.0, 36.6), (41.0, 37.4)], 0.25)
    V("GND", 41.0, 37.4)
    R("GND", [(41.25, 36.6), (41.25, 37.4)], 0.25)
    V("GND", 41.25, 37.4)
    R("GND", [(44.75, 36.6), (44.75, 38.0)], 0.25)
    V("GND", 44.75, 38.0)
    R("GND", [(36.68, 34.1), (36.68, 33.9)], 0.5)
    V("GND", 36.68, 33.9)
    R("GND", [(45.32, 34.1), (45.32, 32.8)], 0.5)
    V("GND", 45.32, 32.8)
    R("GND", [(36.68, 36.7), (36.68, 37.8)], 0.25)
    V("GND", 36.68, 37.8)
    R("GND", [(45.32, 36.7), (45.9, 36.7), (45.9, 37.8)], 0.25)
    V("GND", 45.9, 37.8)

    # ===== silkscreen + zones =====
    pcb.silk_text("ledquad-c3 v1.0", 3.0, 2.0, size=1.2)
    pcb.silk_text("4ch PWM LED 12-24V | MIT | AskAlice", 3.0, 38.6, size=0.8)
    pcb.silk_text("V+ R G B W", 12.0, 30.0, size=0.8)
    pcb.silk_text("12-24V", 4.5, 29.5, size=0.8)
    pcb.keepout_rect(16.5, 0.0, 37.5, 7.0,
                     note="ANTENNA KEEPOUT - no copper all layers")
    pcb.gnd_zone("B.Cu")

    # ===== self-check: prune offending copper, then verify =====
    prob = b.check_courtyards()
    for p in prob:
        print("COPPER:", p)
    if prob:
        raise SystemExit(f"copper self-check failed: {len(prob)} problem(s)")
    removed = b.prune((0.0, 0.0, W, H), [KEEPOUT])
    for kind, net, key in removed:
        print(f"PRUNE: removed {kind} net={net} @ {key}")
    prob = b.check_clearance((0.0, 0.0, W, H), [KEEPOUT])
    for p in prob:
        print("COPPER:", p)
    if prob:
        raise SystemExit(f"copper self-check failed: {len(prob)} problem(s)")
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

    pcb.save(path_pcb())
    return b


# --------------------------------------------------------------------------
# BOM + main
# --------------------------------------------------------------------------
def write_bom(path):
    rows = [
        ("U1", "ESP32-C3-WROOM-02"), ("X1", "USB_C_16P"), ("U2", "AP63205"),
        ("U3", "AP2112K-3.3"), ("Q1,Q2,Q3,Q4", "AO3400A"),
        ("D3,D4", "SS34"), ("F1", "FUSE_5A"), ("L1", "L_4R7"),
        ("J1", "TB_2P"), ("J2", "TB_5P"), ("J3", "Conn_01x04"),
        ("BT1,BT2", "SW_PUSH"),
        ("R1,R2,R3,R4", "100R"), ("R5,R6,R7,R8,R13", "10k"),
        ("R9,R10", "5.1k"), ("R11,R12", "22R"), ("R14,R15", "1k"),
        ("R16", "100k"),
        ("C1,C6,C7,C10", "10uF"), ("C2,C3,C8,C9", "100nF"),
        ("C4,C5", "22uF"), ("D1", "LED_RED"), ("D2", "LED_GRN"),
    ]
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
    build_schematic(os.path.join(OUT, BOARD + ".kicad_sch"),
                    os.path.join(OUT, BOARD + "-lib.kicad_sym"))
    build_pcb(fps)
    write_bom(os.path.join(OUT, "bom_lcsc.csv"))
    problems = kg.validate_project(OUT)
    for p in problems:
        print("VALIDATE:", p)
    if problems:
        raise SystemExit(f"validate_project failed: {len(problems)} problem(s)")
    print("ledquad-c3: project generated + validated")


if __name__ == "__main__":
    main()
