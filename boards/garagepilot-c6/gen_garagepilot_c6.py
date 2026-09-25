#!/usr/bin/env python3
"""garagepilot-c6 -- ESP32-C6 garage-door controller generator.

Generates a self-contained KiCad 8 project with project-local symbol library
and inline footprints.  The board controls a low-voltage garage-door-opener
button circuit (dry relay contact) and reads two magnetic reed switches
(door-closed, door-open) plus an optional safety-beam input.

Run:  python3 gen_garagepilot_c6.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "tools"))
import kicadgen as kg  # noqa: E402

BOARD = "garagepilot-c6"
LIB = f"{BOARD}-lib"
W, H = 100.0, 60.0
OUT = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Part table: value -> (footprint, description, LCSC, MPN, datasheet)
# ---------------------------------------------------------------------------
PARTS = {
    "ESP32-C6-WROOM-1": (f"{LIB}:ESP32-C6-WROOM-1", "Wi-Fi 6 + BLE + 802.15.4 module",
                           "C5366877", "ESP32-C6-WROOM-1-N8",
                           "https://www.espressif.com/sites/default/files/documentation/esp32-c6-wroom-1_wroom-1u_datasheet_en.pdf"),
    "AP2112K-3.3": ("Package_TO_SOT_SMD:SOT-23-5", "LDO 3.3 V 600 mA",
                     "C51115", "AP2112K-3.3TRG1",
                     "https://www.diodes.com/assets/Datasheets/AP2112.pdf"),
    "AO3400A": ("Package_TO_SOT_SMD:SOT-23", "N-channel MOSFET 30 V 5.7 A",
                "C20917", "AO3400A",
                "https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_AOSMD-AO3400A_C20917.pdf"),
    "SRD-05VDC-SL-C": (f"{LIB}:Relay_T73", "5 V SPDT relay 10 A",
                       "C95269", "SRD-05VDC-SL-C",
                       "https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_SONGLE-SRD-05VDC-SL-C_C95269.pdf"),
    "SS34": ("Diode_SMD:D_SMA", "Schottky 40 V 3 A",
             "C8678", "SS34",
             "https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_Guangdong-Hottech-SS34_C8678.pdf"),
    "LED_RED": ("LED_SMD:LED_0603_1608Metric", "LED red 0603",
                "C2286", "LTST-C190KRKT", "~"),
    "10k": ("Resistor_SMD:R_0603_1608Metric", "Resistor 10k 0603",
            "C25804", "0603WAF1002T5E", "~"),
    "4.7k": ("Resistor_SMD:R_0603_1608Metric", "Resistor 4.7k 0603",
             "C23162", "0603WAF4701T5E", "~"),
    "100R": ("Resistor_SMD:R_0603_1608Metric", "Resistor 100R 0603",
             "C22369795", "RCA03100RFLF", "~"),
    "22R": ("Resistor_SMD:R_0603_1608Metric", "Resistor 22R 0603",
            "C22926", "0603WAF220JT5E", "~"),
    "100nF": ("Capacitor_SMD:C_0603_1608Metric", "Cap MLCC 100 nF 0603",
              "C14663", "0603B104K500NT", "~"),
    "10uF": ("Capacitor_SMD:C_0603_1608Metric", "Cap MLCC 10 uF 0603",
             "C15849", "CL10A106KP8NNNC", "~"),
    "SW_PUSH": (f"{LIB}:Tactile-6x6-SMD", "Tactile switch 6x6 SMD",
                "C139797", "TS-1187A-B-A-B", "~"),
    "USB_C_16P": ("Connector_USB:USB_C_Receptacle_USB2.0_16P", "USB-C 2.0 16P mid-mount",
                   "C165948", "TYPE-C-31-M-12",
                   "https://www.lcsc.com/datasheet/lcsc_datasheet_2410252104_Korean-Hroparts-Elec-TYPE-C-31-M-12_C165948.pdf"),
    "Conn_01x04": ("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
                   "Header 1x4 (prog / expansion)", "C49258",
                   "KH-2.54PH180-1X4P-L13.5", "~"),
    "ScrewTerm_2P": (f"{LIB}:ScrewTerm-5.08-2P", "Screw terminal 5.08 mm 2P",
                     "C8465", "WJ500V-5.08-2P", "~"),
    "ScrewTerm_3P": (f"{LIB}:ScrewTerm-5.08-3P", "Screw terminal 5.08 mm 3P",
                     "C8465", "WJ500V-5.08-3P", "~"),
    "TestPoint": (f"{LIB}:TestPoint_Pad_1.0mm", "Test point 1.0 mm SMD pad",
                  "C152136", "Test point", "~"),
}

# ---------------------------------------------------------------------------
# Symbol library
# ---------------------------------------------------------------------------
def build_lib():
    lib = kg.SymbolLib(LIB)

    for p in ("GND", "+3V3", "+5V", "VBUS"):
        lib.add_power_symbol(p)

    # ESP32-C6-WROOM-1
    left = [("1", "GND", "power_in"), ("2", "3V3", "power_in"), ("3", "EN", "input"),
            ("4", "IO4/RELAY", "bidirectional"), ("5", "IO5/IN1", "bidirectional"),
            ("6", "IO6/IN2", "bidirectional"), ("7", "IO7/IN3", "bidirectional"),
            ("8", "IO0", "bidirectional"), ("9", "IO1", "bidirectional"),
            ("10", "IO8/LED", "bidirectional"), ("11", "IO10", "bidirectional"),
            ("12", "IO11", "bidirectional"), ("13", "IO12/USB_DM", "bidirectional"),
            ("14", "IO13/USB_DP", "bidirectional")]
    right = [("15", "IO9/BOOT", "bidirectional"), ("16", "IO18", "bidirectional"),
             ("17", "IO19", "bidirectional"), ("18", "IO20", "bidirectional"),
             ("19", "IO21", "bidirectional"), ("20", "IO22", "bidirectional"),
             ("21", "IO23", "bidirectional"), ("22", "NC", "no_connect"),
             ("23", "IO15", "bidirectional"), ("24", "RXD0/IO17", "bidirectional"),
             ("25", "TXD0/IO16", "bidirectional"), ("26", "IO3", "bidirectional"),
             ("27", "IO2", "bidirectional"), ("28", "GND", "power_in"),
             ("29", "EP/GND", "power_in")]
    pins = []
    for n, name, typ in left:
        pins.append((n, name, typ, "left"))
    for n, name, typ in right:
        pins.append((n, name, typ, "right"))
    lib.add_box_symbol("ESP32-C6-WROOM-1", "U", pins,
                       footprint=PARTS["ESP32-C6-WROOM-1"][0],
                       datasheet=PARTS["ESP32-C6-WROOM-1"][4],
                       lcsc=PARTS["ESP32-C6-WROOM-1"][2],
                       mpn=PARTS["ESP32-C6-WROOM-1"][3])

    # AP2112K-3.3 SOT-23-5
    lib.add_box_symbol("AP2112K-3.3", "U",
                       [("1", "VIN", "power_in", "left"), ("2", "GND", "power_in", "bottom"),
                        ("3", "EN", "input", "left"), ("4", "NC", "no_connect", "right"),
                        ("5", "VOUT", "power_out", "right")],
                       footprint=PARTS["AP2112K-3.3"][0],
                       datasheet=PARTS["AP2112K-3.3"][4],
                       lcsc=PARTS["AP2112K-3.3"][2],
                       mpn=PARTS["AP2112K-3.3"][3])

    # AO3400A SOT-23: 1=G, 2=S, 3=D
    lib.add_box_symbol("AO3400A", "Q",
                       [("1", "G", "input", "left"), ("2", "S", "passive", "right"),
                        ("3", "D", "passive", "right")],
                       footprint=PARTS["AO3400A"][0],
                       datasheet=PARTS["AO3400A"][4],
                       lcsc=PARTS["AO3400A"][2],
                       mpn=PARTS["AO3400A"][3])

    # Relay T73: 1=coil+, 2=coil-, 3=COM, 4=NC, 5=NO
    lib.add_box_symbol("SRD-05VDC-SL-C", "K",
                       [("1", "COIL+", "passive", "left"), ("2", "COIL-", "passive", "left"),
                        ("3", "COM", "passive", "right"), ("4", "NC", "passive", "right"),
                        ("5", "NO", "passive", "right")],
                       footprint=PARTS["SRD-05VDC-SL-C"][0],
                       datasheet=PARTS["SRD-05VDC-SL-C"][4],
                       lcsc=PARTS["SRD-05VDC-SL-C"][2],
                       mpn=PARTS["SRD-05VDC-SL-C"][3])

    # SS34 SMA: 1=K, 2=A
    lib.add_box_symbol("SS34", "D",
                       [("1", "K", "passive", "left"), ("2", "A", "passive", "right")],
                       footprint=PARTS["SS34"][0],
                       datasheet=PARTS["SS34"][4],
                       lcsc=PARTS["SS34"][2],
                       mpn=PARTS["SS34"][3])

    # passives - symbol names must start with a letter; value stays the part value
    PASSIVES = [
        ("R_10k", "10k", "R"),
        ("R_4k7", "4.7k", "R"),
        ("R_100R", "100R", "R"),
        ("R_22R", "22R", "R"),
        ("C_100nF", "100nF", "C"),
        ("C_10uF", "10uF", "C"),
        ("LED_RED", "LED_RED", "D"),
    ]
    for sym, val, prefix in PASSIVES:
        fp, desc, lcsc, mpn, ds = PARTS[val]
        if "LED" in val:
            pins = [("1", "A", "passive", "left"), ("2", "K", "passive", "right")]
        elif "F" in val:
            pins = [("1", "P1", "passive", "left"), ("2", "P2", "passive", "right")]
        else:
            pins = [("1", "~", "passive", "left"), ("2", "~", "passive", "right")]
        lib.add_box_symbol(sym, prefix, pins, footprint=fp, datasheet=ds, lcsc=lcsc, mpn=mpn)

    # USB-C
    lib.add_box_symbol("USB_C_16P", "J",
                       [("1", "GND", "power_in", "right"), ("2", "VBUS", "power_out", "left"),
                        ("3", "CC1", "passive", "left"), ("4", "DP", "passive", "left"),
                        ("5", "DM", "passive", "left"), ("6", "SBU1", "no_connect", "right"),
                        ("7", "VBUS", "power_out", "left"), ("8", "GND", "power_in", "right"),
                        ("9", "GND", "power_in", "right"), ("10", "VBUS", "power_out", "left"),
                        ("11", "SBU2", "no_connect", "right"), ("12", "DM", "passive", "left"),
                        ("13", "DP", "passive", "left"), ("14", "CC2", "passive", "left"),
                        ("15", "VBUS", "power_out", "left"), ("16", "GND", "power_in", "right"),
                        ("S1", "SH", "passive", "right"), ("S2", "SH", "passive", "right"),
                        ("S3", "SH", "passive", "right"), ("S4", "SH", "passive", "right")],
                       footprint=PARTS["USB_C_16P"][0],
                       datasheet=PARTS["USB_C_16P"][4],
                       lcsc=PARTS["USB_C_16P"][2],
                       mpn=PARTS["USB_C_16P"][3])

    # Tactile switch
    lib.add_box_symbol("SW_PUSH", "SW",
                       [("1", "A", "passive", "left"), ("2", "A", "passive", "left"),
                        ("3", "B", "passive", "right"), ("4", "B", "passive", "right")],
                       footprint=PARTS["SW_PUSH"][0],
                       datasheet=PARTS["SW_PUSH"][4],
                       lcsc=PARTS["SW_PUSH"][2],
                       mpn=PARTS["SW_PUSH"][3])

    # Terminal blocks
    lib.add_box_symbol("ScrewTerm_2P", "J",
                       [("1", "1", "passive", "top"), ("2", "2", "passive", "top")],
                       footprint=PARTS["ScrewTerm_2P"][0],
                       datasheet=PARTS["ScrewTerm_2P"][4],
                       lcsc=PARTS["ScrewTerm_2P"][2],
                       mpn=PARTS["ScrewTerm_2P"][3])
    lib.add_box_symbol("ScrewTerm_3P", "J",
                       [("1", "1", "passive", "top"), ("2", "2", "passive", "top"),
                        ("3", "3", "passive", "top")],
                       footprint=PARTS["ScrewTerm_3P"][0],
                       datasheet=PARTS["ScrewTerm_3P"][4],
                       lcsc=PARTS["ScrewTerm_3P"][2],
                       mpn=PARTS["ScrewTerm_3P"][3])

    # 1x4 header
    lib.add_box_symbol("Conn_01x04", "J",
                       [("1", "1", "passive", "top"), ("2", "2", "passive", "top"),
                        ("3", "3", "passive", "top"), ("4", "4", "passive", "top")],
                       footprint=PARTS["Conn_01x04"][0],
                       datasheet=PARTS["Conn_01x04"][4],
                       lcsc=PARTS["Conn_01x04"][2],
                       mpn=PARTS["Conn_01x04"][3])

    # Test point
    lib.add_box_symbol("TestPoint", "TP",
                       [("1", "1", "passive", "top")],
                       footprint=PARTS["TestPoint"][0],
                       datasheet=PARTS["TestPoint"][4],
                       lcsc=PARTS["TestPoint"][2],
                       mpn=PARTS["TestPoint"][3])

    return lib

# ---------------------------------------------------------------------------
# Footprints
# ---------------------------------------------------------------------------
def build_footprints(lib):
    fps = {}

    # ESP32-C6-WROOM-1 ( pads 1-14 left, 15-28 right, 29 EP )
    fp = kg.Footprint(lib, "ESP32-C6-WROOM-1")
    for i in range(14):
        fp.add_pad(str(i + 1), "smd", "rect", -8.75, 8.255 - i * 1.27, 1.5, 0.9)
    for i in range(14):
        fp.add_pad(str(28 - i), "smd", "rect", 8.75, 8.255 - i * 1.27, 1.5, 0.9)
    fp.add_pad("29", "smd", "rect", 0.0, 0.0, 7.5, 12.3)
    fp.add_rect(-9.0, -12.75, 9.0, 12.75, "F.Fab", 0.1)
    fp.add_rect(-9.5, -13.25, 9.5, 13.25, "F.CrtYd", 0.05)
    fp.add_line(-9.0, -12.75, 9.0, -12.75, "F.SilkS")
    fp.add_line(-9.0, -12.75, -9.0, -5.0, "F.SilkS")
    fp.add_line(9.0, -12.75, 9.0, -5.0, "F.SilkS")
    fp.add_line(-9.0, 5.0, -9.0, 12.75, "F.SilkS")
    fp.add_line(9.0, 5.0, 9.0, 12.75, "F.SilkS")
    fp.add_line(-9.0, 12.75, 9.0, 12.75, "F.SilkS")
    fp.add_text("ANT", 0.0, -10.5, "F.SilkS", 0.8)
    fps["ESP32-C6-WROOM-1"] = fp

    # Tactile 6x6 SMD
    fp = kg.Footprint(lib, "Tactile-6x6-SMD")
    for num, x, y in (("1", -4.5, -2.25), ("2", 4.5, -2.25),
                      ("3", -4.5, 2.25), ("4", 4.5, 2.25)):
        fp.add_pad(num, "smd", "rect", x, y, 2.3, 1.5)
    fp.add_rect(-3.0, -3.0, 3.0, 3.0, "F.Fab", 0.1)
    fp.add_rect(-5.95, -3.15, 5.95, 3.15, "F.CrtYd", 0.05)
    fp.add_rect(-3.0, -3.0, 3.0, 3.0, "F.SilkS", 0.12)
    fps["Tactile-6x6-SMD"] = fp

    # Relay T73 / SRD-05VDC-SL-C
    fp = kg.Footprint(lib, "Relay_T73")
    fp.add_pad("1", "thru_hole", "circle", -7.5, -5.75, 1.8, 1.8,
               layers=("*.Cu", "*.Mask"), drill=1.0)
    fp.add_pad("2", "thru_hole", "circle", -7.5, 5.75, 1.8, 1.8,
               layers=("*.Cu", "*.Mask"), drill=1.0)
    fp.add_pad("3", "thru_hole", "circle", 7.5, 0.0, 1.8, 1.8,
               layers=("*.Cu", "*.Mask"), drill=1.0)
    fp.add_pad("4", "thru_hole", "circle", 7.5, 3.81, 1.8, 1.8,
               layers=("*.Cu", "*.Mask"), drill=1.0)
    fp.add_pad("5", "thru_hole", "circle", 7.5, -3.81, 1.8, 1.8,
               layers=("*.Cu", "*.Mask"), drill=1.0)
    fp.add_rect(-9.5, -8.0, 9.5, 8.0, "F.Fab", 0.1)
    fp.add_rect(-10.5, -9.0, 10.5, 9.0, "F.CrtYd", 0.05)
    fp.add_line(-9.5, -8.0, 9.5, -8.0, "F.SilkS")
    fp.add_line(-9.5, 8.0, 9.5, 8.0, "F.SilkS")
    fp.add_line(-9.5, -8.0, -9.5, 8.0, "F.SilkS")
    fp.add_line(9.5, -8.0, 9.5, 8.0, "F.SilkS")
    fp.add_text("K1", -6.0, 0.0, "F.SilkS", 1.0)
    fps["Relay_T73"] = fp

    # Screw terminals 5.08 mm pitch
    for p, n in (("ScrewTerm-5.08-2P", 2), ("ScrewTerm-5.08-3P", 3)):
        fp = kg.Footprint(lib, p)
        start = -((n - 1) * 5.08) / 2
        for i in range(n):
            fp.add_pad(str(i + 1), "thru_hole", "rect" if i == 0 else "circle",
                       start + i * 5.08, 0.0, 2.2, 2.2,
                       layers=("*.Cu", "*.Mask"), drill=1.2)
        hw = abs(start) + 2.54 + 1.0
        fp.add_rect(-hw, -2.5, hw, 2.5, "F.Fab", 0.1)
        fp.add_rect(-hw - 0.5, -3.0, hw + 0.5, 3.0, "F.CrtYd", 0.05)
        fp.add_line(-hw, -2.5, hw, -2.5, "F.SilkS")
        fp.add_line(-hw, 2.5, hw, 2.5, "F.SilkS")
        fp.add_line(-hw, -2.5, -hw, 2.5, "F.SilkS")
        fp.add_line(hw, -2.5, hw, 2.5, "F.SilkS")
        fps[p] = fp

    # Test point 1.0 mm SMD pad
    fp = kg.Footprint(lib, "TestPoint_Pad_1.0mm")
    fp.add_pad("1", "smd", "circle", 0.0, 0.0, 1.0, 1.0)
    fp.add_circle(0.0, 0.0, 0.75, "F.SilkS")
    fp.add_circle(0.0, 0.0, 1.0, "F.CrtYd", 0.05)
    fps["TestPoint_Pad_1.0mm"] = fp

    return fps

# ---------------------------------------------------------------------------
# Schematic
# ---------------------------------------------------------------------------
U1_PLAN = {
    "1": "GND", "2": "+3V3", "3": "EN", "4": "RELAY_DRV", "5": "INPUT1",
    "6": "INPUT2", "7": "INPUT3", "8": None, "9": None, "10": "LED1_A",
    "11": None, "12": None, "13": None, "14": None, "15": "BOOT",
    "16": None, "17": None, "18": None, "19": None, "20": None, "21": None,
    "22": None, "23": None, "24": "RX0", "25": "TX0", "26": None, "27": None,
    "28": "GND", "29": "GND",
}
U2_PLAN = {"1": "VBUS", "2": "GND", "3": "+3V3", "4": None, "5": "+3V3"}
Q1_PLAN = {"1": "RELAY_DRV", "2": "GND", "3": "K1_COIL_P"}
K1_PLAN = {"1": "+5V", "2": "K1_COIL_P", "3": "RELAY_COM", "4": "RELAY_NC", "5": "RELAY_NO"}
D1_PLAN = {"1": "+5V", "2": "K1_COIL_P"}   # SS34 flyback cathode to +5V
D2_PLAN = {"1": "LED1_A", "2": "GND"}      # LED red anode via resistor
R_LED_PLAN = {"1": "+3V3", "2": "LED1_A"}
R_GATE_PLAN = {"1": "RELAY_DRV", "2": "Q1_GATE"}
R_IN1_PLAN = {"1": "+3V3", "2": "INPUT1"}
R_IN2_PLAN = {"1": "+3V3", "2": "INPUT2"}
R_IN3_PLAN = {"1": "+3V3", "2": "INPUT3"}
R_EN_PLAN = {"1": "+3V3", "2": "EN"}
R_BOOT_PLAN = {"1": "+3V3", "2": "BOOT"}
C1_PLAN = {"1": "VBUS", "2": "GND"}
C2_PLAN = {"1": "+3V3", "2": "GND"}
C3_PLAN = {"1": "+3V3", "2": "GND"}
BT1_PLAN = {"1": "EN", "2": "GND", "3": "EN", "4": "GND"}
BT2_PLAN = {"1": "BOOT", "2": "GND", "3": "BOOT", "4": "GND"}


def _resolve(sch, ref, plan):
    for pad, net in plan.items():
        if net is None:
            sch.no_connect(*sch.pin_at(ref, pad))
        else:
            sch.label(net, *sch.pin_at(ref, pad))


def build_schematic(lib):
    sch = kg.Schematic("GaragePilot C6", lib)
    sch.sheet_note("Garage door controller: ESP32-C6 + relay + 3x inputs")
    sch.sheet_note("USB-C or 5 V terminal power; LDO 3.3 V; dry relay contact")

    # Main parts
    sch.place("ESP32-C6-WROOM-1", "U1", 100, 120, value="ESP32-C6-WROOM-1-N8")
    _resolve(sch, "U1", U1_PLAN)
    sch.place("AP2112K-3.3", "U2", 45, 80, value="AP2112K-3.3")
    _resolve(sch, "U2", U2_PLAN)
    sch.place("AO3400A", "Q1", 150, 80, value="AO3400A")
    _resolve(sch, "Q1", Q1_PLAN)
    sch.place("SRD-05VDC-SL-C", "K1", 190, 85, value="SRD-05VDC-SL-C")
    _resolve(sch, "K1", K1_PLAN)
    sch.place("SS34", "D1", 165, 55, value="SS34")
    _resolve(sch, "D1", D1_PLAN)
    sch.place("LED_RED", "D2", 110, 50, value="LED_RED")
    _resolve(sch, "D2", D2_PLAN)

    # Resistors / capacitors
    placements = [
        ("R_10k", "10k", "R1", 90, 50, R_LED_PLAN),
        ("R_100R", "100R", "R2", 130, 80, R_GATE_PLAN),
        ("R_10k", "10k", "R3", 80, 155, R_IN1_PLAN),
        ("R_10k", "10k", "R4", 95, 155, R_IN2_PLAN),
        ("R_10k", "10k", "R5", 110, 155, R_IN3_PLAN),
        ("R_10k", "10k", "R10", 70, 175, R_EN_PLAN),
        ("R_10k", "10k", "R11", 140, 175, R_BOOT_PLAN),
        ("C_10uF", "10uF", "C1", 35, 50, C1_PLAN),
        ("C_10uF", "10uF", "C2", 20, 50, C2_PLAN),
        ("C_100nF", "100nF", "C3", 60, 50, C3_PLAN),
    ]
    for sym, val, ref, x, y, plan in placements:
        sch.place(sym, ref, x, y, value=val)
        _resolve(sch, ref, plan)

    # Switches
    sch.place("SW_PUSH", "SW1", 130, 165, value="RESET")
    _resolve(sch, "SW1", BT1_PLAN)
    sch.place("SW_PUSH", "SW2", 160, 165, value="BOOT")
    _resolve(sch, "SW2", BT2_PLAN)

    # USB-C
    sch.place("USB_C_16P", "J1", 20, 130, value="USB_C_16P")
    for pad, net in {
        "1": "GND", "2": "VBUS", "3": "USB_CC1", "4": "USB_DP", "5": "USB_DM",
        "7": "VBUS", "8": "GND", "9": "GND", "10": "VBUS",
        "12": "USB_DM", "13": "USB_DP", "14": "USB_CC2", "15": "VBUS", "16": "GND",
        "S1": "GND", "S2": "GND", "S3": "GND", "S4": "GND",
    }.items():
        sch.label(net, *sch.pin_at("J1", pad))
    sch.no_connect(*sch.pin_at("J1", "6"))
    sch.no_connect(*sch.pin_at("J1", "11"))

    # CC pulldowns
    sch.place("R_4k7", "R6", 35, 115, value="4.7k")
    sch.label("USB_CC1", *sch.pin_at("R6", "1"))
    sch.label("GND", *sch.pin_at("R6", "2"))
    sch.place("R_4k7", "R7", 35, 145, value="4.7k")
    sch.label("USB_CC2", *sch.pin_at("R7", "1"))
    sch.label("GND", *sch.pin_at("R7", "2"))

    # USB series resistors
    sch.place("R_22R", "R8", 50, 105, value="22R")
    sch.label("USB_DP", *sch.pin_at("R8", "1"))
    sch.label("USB_DP_FILT", *sch.pin_at("R8", "2"))
    sch.place("R_22R", "R9", 50, 155, value="22R")
    sch.label("USB_DM", *sch.pin_at("R9", "1"))
    sch.label("USB_DM_FILT", *sch.pin_at("R9", "2"))

    # Wire USB filtered side to module pins
    sch.wire([sch.pin_at("U1", "13"), (85, 145)])
    sch.label("USB_DM_FILT", 85, 145)
    sch.wire([sch.pin_at("U1", "14"), (85, 105)])
    sch.label("USB_DP_FILT", 85, 105)

    # Terminal blocks
    sch.place("ScrewTerm_3P", "J2", 230, 130, value="RELAY")
    for pad, net in {"1": "RELAY_NO", "2": "RELAY_COM", "3": "RELAY_NC"}.items():
        sch.label(net, *sch.pin_at("J2", pad))
    sch.place("ScrewTerm_3P", "J3", 230, 165, value="INPUTS")
    for pad, net in {"1": "INPUT1", "2": "INPUT2", "3": "INPUT3"}.items():
        sch.label(net, *sch.pin_at("J3", pad))
    sch.place("ScrewTerm_2P", "J4", 230, 195, value="AUX_5V")
    sch.label("+5V", *sch.pin_at("J4", "1"))
    sch.label("GND", *sch.pin_at("J4", "2"))

    # Programming / expansion header
    sch.place("Conn_01x04", "J5", 60, 190, value="PROG")
    for pad, net in {"1": "+3V3", "2": "TX0", "3": "RX0", "4": "GND"}.items():
        sch.label(net, *sch.pin_at("J5", pad))

    # Test points
    for tp, net, x, y in (("TP1", "+5V", 30, 30), ("TP2", "+3V3", 40, 30),
                          ("TP3", "GND", 50, 30), ("TP4", "RELAY_DRV", 60, 30)):
        sch.place("TestPoint", tp, x, y, value=net)
        sch.label(net, *sch.pin_at(tp, "1"))

    # Power rails
    for i, name in enumerate(("GND", "+3V3", "+5V", "VBUS")):
        x, y = 15 + 10 * i, 25
        sch.place_power(name, x, y)
        sch.label(name, x, y)

    return sch

# ---------------------------------------------------------------------------
# PCB
# ---------------------------------------------------------------------------
def rot_pt(x, y, deg):
    r = math.radians(deg)
    c, s = round(math.cos(r)), round(math.sin(r))
    return x * c - y * s, x * s + y * c


def build_pcb(fps):
    pcb = kg.PCB("GaragePilot C6")
    pcb.set_outline(W, H)
    pcb.add_mounting_holes(inset=10.0)

    def add(fp, ref, val, x, y, rot=0):
        pcb.add_footprint(fps.get(fp, fp), ref, val, x, y, rot)

    # Core components - spread out on a 100 x 60 mm board
    add("ESP32-C6-WROOM-1", "U1", "ESP32-C6-WROOM-1-N8", 35.0, 30.0, 0)
    add("Package_TO_SOT_SMD:SOT-23-5", "U2", "AP2112K-3.3", 20.0, 42.0, 0)
    add("Package_TO_SOT_SMD:SOT-23", "Q1", "AO3400A", 62.0, 22.0, 0)
    add("Relay_T73", "K1", "SRD-05VDC-SL-C", 55.0, 40.0, 0)
    add("Diode_SMD:D_SMA", "D1", "SS34", 72.0, 22.0, 0)
    add("LED_SMD:LED_0603_1608Metric", "D2", "LED_RED", 22.0, 12.0, 0)

    # Passives
    add("Resistor_SMD:R_0603_1608Metric", "R1", "10k", 26.0, 12.0, 0)
    add("Resistor_SMD:R_0603_1608Metric", "R2", "100R", 56.0, 22.0, 0)
    add("Resistor_SMD:R_0603_1608Metric", "R3", "10k", 50.0, 26.0, 90)
    add("Resistor_SMD:R_0603_1608Metric", "R4", "10k", 55.0, 26.0, 90)
    add("Resistor_SMD:R_0603_1608Metric", "R5", "10k", 60.0, 26.0, 90)
    add("Resistor_SMD:R_0603_1608Metric", "R6", "4.7k", 21.0, 24.0, 90)
    add("Resistor_SMD:R_0603_1608Metric", "R7", "4.7k", 21.0, 28.0, 90)
    add("Resistor_SMD:R_0603_1608Metric", "R8", "22R", 24.0, 22.0, 90)
    add("Resistor_SMD:R_0603_1608Metric", "R9", "22R", 24.0, 26.0, 90)
    add("Resistor_SMD:R_0603_1608Metric", "R10", "10k", 28.0, 45.0, 0)
    add("Resistor_SMD:R_0603_1608Metric", "R11", "10k", 42.0, 45.0, 0)

    add("Capacitor_SMD:C_0603_1608Metric", "C1", "10uF", 12.0, 36.0, 0)
    add("Capacitor_SMD:C_0603_1608Metric", "C2", "10uF", 20.0, 36.0, 0)
    add("Capacitor_SMD:C_0603_1608Metric", "C3", "100nF", 26.0, 48.0, 0)

    # Switches / connectors
    add("Tactile-6x6-SMD", "SW1", "RESET", 30.0, 8.0, 0)
    add("Tactile-6x6-SMD", "SW2", "BOOT", 46.0, 8.0, 0)
    add("Connector_USB:USB_C_Receptacle_USB2.0_16P", "J1", "USB_C_16P", 13.0, 30.0, 0)
    add("ScrewTerm-5.08-3P", "J2", "RELAY", 78.0, 26.0, 90)
    add("ScrewTerm-5.08-3P", "J3", "INPUTS", 78.0, 46.0, 90)
    add("ScrewTerm-5.08-2P", "J4", "AUX_5V", 78.0, 7.0, 90)
    add("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", "J5", "PROG", 15.0, 8.0, 0)

    # Test points
    for tp, val, x, y in (("TP1", "+5V", 6.0, 8.0), ("TP2", "+3V3", 19.0, 8.0),
                          ("TP3", "GND", 6.0, 52.0), ("TP4", "RELAY_DRV", 54.0, 8.0)):
        add("TestPoint_Pad_1.0mm", tp, val, x, y, 0)

    # -----------------------------------------------------------------------
    # Net assignments
    # -----------------------------------------------------------------------
    nets = {
        ("U1", "1"): "GND", ("U1", "2"): "+3V3", ("U1", "3"): "EN",
        ("U1", "4"): "RELAY_DRV", ("U1", "5"): "INPUT1", ("U1", "6"): "INPUT2",
        ("U1", "7"): "INPUT3", ("U1", "10"): "LED1_A",
        ("U1", "13"): "USB_DM_FILT", ("U1", "14"): "USB_DP_FILT",
        ("U1", "15"): "BOOT", ("U1", "24"): "RX0", ("U1", "25"): "TX0",
        ("U1", "28"): "GND", ("U1", "29"): "GND",
        ("U2", "1"): "VBUS", ("U2", "2"): "GND", ("U2", "3"): "+3V3",
        ("U2", "5"): "+3V3",
        ("Q1", "1"): "Q1_GATE", ("Q1", "2"): "GND", ("Q1", "3"): "K1_COIL_P",
        ("K1", "1"): "+5V", ("K1", "2"): "K1_COIL_P",
        ("K1", "3"): "RELAY_COM", ("K1", "4"): "RELAY_NC", ("K1", "5"): "RELAY_NO",
        ("D1", "1"): "+5V", ("D1", "2"): "K1_COIL_P",
        ("D2", "1"): "LED1_A", ("D2", "2"): "GND",
        ("R1", "1"): "+3V3", ("R1", "2"): "LED1_A",
        ("R2", "1"): "RELAY_DRV", ("R2", "2"): "Q1_GATE",
        ("R3", "1"): "+3V3", ("R3", "2"): "INPUT1",
        ("R4", "1"): "+3V3", ("R4", "2"): "INPUT2",
        ("R5", "1"): "+3V3", ("R5", "2"): "INPUT3",
        ("R6", "1"): "USB_CC1", ("R6", "2"): "GND",
        ("R7", "1"): "USB_CC2", ("R7", "2"): "GND",
        ("R8", "1"): "USB_DP", ("R8", "2"): "USB_DP_FILT",
        ("R9", "1"): "USB_DM", ("R9", "2"): "USB_DM_FILT",
        ("R10", "1"): "+3V3", ("R10", "2"): "EN",
        ("R11", "1"): "+3V3", ("R11", "2"): "BOOT",
        ("C1", "1"): "VBUS", ("C1", "2"): "GND",
        ("C2", "1"): "+3V3", ("C2", "2"): "GND",
        ("C3", "1"): "+3V3", ("C3", "2"): "GND",
        ("SW1", "1"): "EN", ("SW1", "2"): "GND",
        ("SW1", "3"): "EN", ("SW1", "4"): "GND",
        ("SW2", "1"): "BOOT", ("SW2", "2"): "GND",
        ("SW2", "3"): "BOOT", ("SW2", "4"): "GND",
        ("J1", "1"): "GND", ("J1", "2"): "VBUS", ("J1", "3"): "USB_CC1",
        ("J1", "4"): "USB_DP", ("J1", "5"): "USB_DM",
        ("J1", "7"): "VBUS", ("J1", "8"): "GND", ("J1", "9"): "GND",
        ("J1", "10"): "VBUS", ("J1", "12"): "USB_DM", ("J1", "13"): "USB_DP",
        ("J1", "14"): "USB_CC2", ("J1", "15"): "VBUS", ("J1", "16"): "GND",
        ("J1", "S1"): "GND", ("J1", "S2"): "GND",
        ("J1", "S3"): "GND", ("J1", "S4"): "GND",
        ("J2", "1"): "RELAY_NO", ("J2", "2"): "RELAY_COM", ("J2", "3"): "RELAY_NC",
        ("J3", "1"): "INPUT1", ("J3", "2"): "INPUT2", ("J3", "3"): "INPUT3",
        ("J4", "1"): "+5V", ("J4", "2"): "GND",
        ("J5", "1"): "+3V3", ("J5", "2"): "TX0", ("J5", "3"): "RX0", ("J5", "4"): "GND",
        ("TP1", "1"): "+5V", ("TP2", "1"): "+3V3", ("TP3", "1"): "GND",
        ("TP4", "1"): "RELAY_DRV",
    }
    for (ref, pad), net in nets.items():
        try:
            pcb.set_pad_net(ref, pad, net)
        except ValueError as e:
            print(f"warn: {e}")

    # Pad absolute position helper
    pad_xy = {}
    for f in pcb._footprints:
        fp, x, y, rot = f["fp"], f["x"], f["y"], f["rot"]
        for p in fp.pads:
            dx, dy = rot_pt(p["x"], p["y"], rot)
            pad_xy[(f["ref"], p["num"])] = (x + dx, y + dy)

    def pxy(ref, pad):
        return pad_xy[(ref, pad)]

    # -----------------------------------------------------------------------
    # Routing
    # -----------------------------------------------------------------------
    # Copper is left unrouted here so the project can be exported to Specctra
    # DSN and autorouted (e.g. with the freeroute Python autorouter).  The
    # GND pour on B.Cu and component placements are retained; silkscreen and
    # keepout are added below.
    pcb.gnd_zone("B.Cu")

    # Silkscreen
    pcb.silk_text("GaragePilot C6", 50.0, 57.0, size=1.5)
    pcb.silk_text("IO4=RELAY 5=IN1 6=IN2 7=IN3", 50.0, 2.0, size=0.8)
    pcb.silk_text("ANT KEEPOUT", 35.0, 14.0, size=0.8)
    pcb.silk_text("+5V AUX", 78.0, 5.0, size=0.8)
    pcb.silk_text("RELAY", 78.0, 18.0, size=0.8)
    pcb.silk_text("INPUTS", 78.0, 36.0, size=0.8)

    # Antenna keepout below the ESP32-C6-WROOM-1 module (antenna at bottom edge)
    pcb.keepout_rect(28.0, 11.0, 42.0, 17.25, note="ESP32-C6 antenna keepout")

    # 3D model attachments (local project-relative models)
    _MODEL_PATHS = {
        "U1": "ESP32-C6-WROOM-1.STEP",
        "U2": "SOT-23-5.step",
        "Q1": "SOT-23.step",
        "D1": "D_SMA.step",
        "D2": "LED_0603_1608Metric.step",
        "K1": "Relay_SPDT_SANYOU_SRD_Series_Form_C.step",
        "J1": "USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.step",
        "J5": "PinHeader_1x04_P2.54mm_Vertical.step",
        "SW1": "SW_Push_1P1T_NO_E-Switch_TL3301NxxxxxG.step",
        "SW2": "SW_Push_1P1T_NO_E-Switch_TL3301NxxxxxG.step",
    }
    for ref, model in _MODEL_PATHS.items():
        pcb.footprint_model(ref, f"${{KIPRJMOD}}/3dmodels/{model}")
    for ref in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11"):
        pcb.footprint_model(ref, "${KIPRJMOD}/3dmodels/R_0603_1608Metric.step")
    for ref in ("C1", "C2", "C3"):
        pcb.footprint_model(ref, "${KIPRJMOD}/3dmodels/C_0603_1608Metric.step")
    # Phoenix terminal blocks are modelled with pin 1 at the model origin, but
    # our footprints are centered on the pin row; offset to align pin 1.
    pcb.footprint_model(
        "J4", "${KIPRJMOD}/3dmodels/TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal.step",
        offset=(-2.54, 0.0, 0.0))
    for ref in ("J2", "J3"):
        pcb.footprint_model(
            ref, "${KIPRJMOD}/3dmodels/TerminalBlock_Phoenix_MKDS-1,5-3-5.08_1x03_P5.08mm_Horizontal.step",
            offset=(-5.08, 0.0, 0.0))

    return pcb


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    lib = build_lib()
    lib.save(os.path.join(OUT, f"{LIB}.kicad_sym"))

    sch = build_schematic(lib)
    sch.save(os.path.join(OUT, f"{BOARD}.kicad_sch"))

    fps = build_footprints(LIB)
    pcb = build_pcb(fps)
    pcb.save(os.path.join(OUT, f"{BOARD}.kicad_pcb"))

    kg.write_project(os.path.join(OUT, f"{BOARD}.kicad_pro"),
                     "GaragePilot C6", LIB)

    issues = kg.validate_project(OUT)
    if issues:
        print(f"WARN: {len(issues)} issue(s):")
        for i in issues:
            print("  -", i)
    else:
        print("OK: project validates")
