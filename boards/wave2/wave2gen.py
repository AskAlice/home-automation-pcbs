#!/usr/bin/env python3
"""wave2gen -- shared generator for the six wave-2 v0.1 concept boards.

Boards: threadnode-h2, airquality-s3, blinddriver-c6, irblaster-c3,
gardenprobe-c6, threadrcp-h2.  Each board is a compact spec using the
helpers here; the heavy lifting (symbols, schematic resolution, PCB
emission, geometric self-check, BOM) is shared.

Module footprints are built from the OFFICIAL Espressif KiCad library
pad coordinates (https://github.com/espressif/kicad-libraries ,
footprints/Espressif.pretty/*.kicad_mod, fetched 2025) and the Espressif
module datasheets:
  * ESP32-H2-MINI-1 : https://documentation.espressif.com/esp32-h2-mini-1_mini-1u_datasheet_en.html
                      (13.2 x 16.6 mm, 53 pads; antenna at pin-1 end)
  * ESP32-S3-WROOM-1: https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf
                      (18 x 25.5 mm, 40 pads + EP; antenna at pin-1 end)
  * ESP32-C6-WROOM-1: https://www.espressif.com/sites/default/files/documentation/esp32-c6-wroom-1_wroom-1u_datasheet_en.pdf
  * ESP32-C3-WROOM-02: https://www.espressif.com/sites/default/files/documentation/esp32-c3-wroom-02_datasheet_en.pdf
Sensirion sensor pinouts verified against the manufacturer datasheets:
  * SHT40 DFN-4 : 1=SDA 2=SCL 3=VDD 4=VSS  (sensirion.com/resource/datasheet/sht4x)
  * SGP40 DFN-6 : 1=VDD 2=VSS 3=SDA 4=NC(GND) 5=VDDH 6=SCL (sensirion.com/resource/datasheet/sgp40)
  * SCD40       : 1=SCL 2=GND 3=VDD 4=SDA  (Sensirion SCD4x datasheet)
Verify all custom footprints against the datasheets before fabrication.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "tools"))
import kicadgen as kg  # noqa: E402

WAVE2 = os.path.dirname(os.path.abspath(__file__))
BOARDS_ROOT = os.path.dirname(WAVE2)

# ---------------------------------------------------------------------------
# LCSC part table (jlcsearch API, queried 2025; C-numbers + stock verified)
# value -> (footprint, lcsc, mpn, datasheet)
# ---------------------------------------------------------------------------
DS_ESPRESSIF = "https://github.com/espressif/kicad-libraries"
PARTS = {
    "ESP32-H2-MINI-1": ("custom:ESP32-H2-MINI-1", "—",
                        "ESP32-H2-MINI-1-N4",
                        "https://documentation.espressif.com/esp32-h2-mini-1_mini-1u_datasheet_en.html"),
    "ESP32-S3-WROOM-1": ("custom:ESP32-S3-WROOM-1", "C2913198",
                         "ESP32-S3-WROOM-1-N8",
                         "https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf"),
    "ESP32-C6-WROOM-1": ("custom:ESP32-C6-WROOM-1", "C5366877",
                         "ESP32-C6-WROOM-1-N8",
                         "https://www.espressif.com/sites/default/files/documentation/esp32-c6-wroom-1_wroom-1u_datasheet_en.pdf"),
    "ESP32-C3-WROOM-02": ("custom:ESP32-C3-WROOM-02", "C2934560",
                          "ESP32-C3-WROOM-02-N4",
                          "https://www.espressif.com/sites/default/files/documentation/esp32-c3-wroom-02_datasheet_en.pdf"),
    "USB_C_16P": ("Connector_USB:USB_C_Receptacle_USB2.0_16P", "C165948",
                  "TYPE-C-31-M-12",
                  "https://www.lcsc.com/datasheet/lcsc_datasheet_2410252104_Korean-Hroparts-Elec-TYPE-C-31-M-12_C165948.pdf"),
    "AP2112K-3.3": ("Package_TO_SOT_SMD:SOT-23-5", "C51115", "AP2112K-3.3TRG1",
                    "https://www.diodes.com/assets/Datasheets/AP2112.pdf"),
    "MCP1700-3302": ("Package_TO_SOT_SMD:SOT-23", "C39051", "MCP1700T-3302E/TT",
                     "https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MCP1700-Data-Sheet-20001826F.pdf"),
    "AP63205": ("Package_TO_SOT_SMD:SOT-23-6", "C2071056", "AP63205WU-7",
                "https://www.diodes.com/assets/Datasheets/AP63200-AP63201-AP63203-AP63205.pdf"),
    "AO3401A": ("Package_TO_SOT_SMD:SOT-23", "C15127", "AO3401A",
                "https://www.lcsc.com/datasheet/lcsc_datasheet_1811151611_AOSMD-AO3401A_C15127.pdf"),
    "S8050": ("Package_TO_SOT_SMD:SOT-23", "C2146", "S8050 J3Y",
              "https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_JSCJ-S8050-J3Y_C2146.pdf"),
    "SS34": ("Diode_SMD:D_SMA", "C8678", "SS34",
             "https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_Guangdong-Hottech-SS34_C8678.pdf"),
    "SCD40": ("custom:SCD40", "C3659421", "SCD40-D-R2",
              "https://sensirion.com/resource/datasheet/scd40"),
    "SGP40": ("custom:SGP40-DFN6", "C2874215", "SGP40-D-R4",
              "https://sensirion.com/resource/datasheet/sgp40"),
    "SHT40": ("custom:SHT40-DFN4", "C2909890", "SHT40-AD1B-R2",
              "https://sensirion.com/resource/datasheet/sht4x"),
    "SHT31": ("custom:SHT31-DFN8", "C80862", "SHT31-DIS-B2.5kS",
              "https://www.sensirion.com/media/documents/213E6A3B/63A5A569/Datasheet_SHT3x_DIS.pdf"),
    "BH1750": ("custom:BH1750-WSOF6", "C78960", "BH1750FVI-TR",
               "https://www.mouser.com/datasheet/2/348/bh1750fvi-e-1868571.pdf"),
    "TMC2209": ("custom:TMC2209-socket", "C2150710", "TMC2209-LA-T",
                "https://www.analog.com/media/en/technical-documentation/data-sheets/tmc2209_datasheet_rev1.09.pdf"),
    "CR2032_HOLDER": ("custom:CR2032-holder", "C5239862", "BS-02-A1AJ010",
                      "https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_SHOU-HAN-BS-02-A1AJ010_C5239862.pdf"),
    "JST_PH_2": ("custom:JST-PH-2", "C131337", "B2B-PH-K-S(LF)(SN)",
                 "https://www.jst-mfg.com/product/pdf/eng/ePH.pdf"),
    "SOIL_PROBE": ("custom:SoilProbe-BCu", "—",
                   "copper electrodes on B.Cu (ENIG recommended)", "~"),
    "REED": ("custom:Reed-SMD", "C315909", "59170-1-S-00-D",
             "https://www.littelfuse.com/assetdocs/reed-sensor-59170-datasheet"),
    "TSOP38238": ("custom:TSOP38238", "C141632", "TSOP38238",
                  "https://www.vishay.com/docs/82491/tsop382.pdf"),
    "TSAL6200": ("custom:IR-LED-5mm", "C55528", "TSAL6200",
                 "https://www.vishay.com/docs/81010/tsal6200.pdf"),
    "100uF_35V": ("Capacitor_SMD:CP_Electrolytic_5x5.3", "C2836437",
                  "RVE100UF35V67RV0072",
                  "https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_ROQANG-RVE100UF35V67RV0072_C2836437.pdf"),
    "4.7uH": ("custom:IND-4040", "C167874", "FNR4030S4R7MT",
              "https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_cjiang-FNR4030S4R7MT_C167874.pdf"),
    # passives / misc (0603 basic parts)
    "10k": ("Resistor_SMD:R_0603_1608Metric", "C25804", "0603WAF1002T5E", "~"),
    "4.7k": ("Resistor_SMD:R_0603_1608Metric", "C23162", "0603WAF4701T5E", "~"),
    "5.1k": ("Resistor_SMD:R_0603_1608Metric", "C23186", "0603WAF5101T5E", "~"),
    "2.2k": ("Resistor_SMD:R_0603_1608Metric", "C2907005", "FRC0603F2201TS", "~"),
    "22R": ("Resistor_SMD:R_0603_1608Metric", "C22926", "0603WAF220JT5E", "~"),
    "47R": ("Resistor_SMD:R_0603_1608Metric", "C2907043", "FRC0603F47R0TS", "~"),
    "100R": ("Resistor_SMD:R_0603_1608Metric", "C22369795", "RCA03100RFLF", "~"),
    "100k": ("Resistor_SMD:R_0603_1608Metric", "C25803", "0603WAF1003T5E", "~"),
    "1M": ("Resistor_SMD:R_0603_1608Metric", "C269433", "RMC06031M5%N", "~"),
    "1k": ("Resistor_SMD:R_0603_1608Metric", "C21190", "0603WAF1001T5E", "~"),
    "100nF": ("Capacitor_SMD:C_0603_1608Metric", "C14663", "0603B104K500NT", "~"),
    "1uF": ("Capacitor_SMD:C_0603_1608Metric", "C52923", "0603B105K500NT", "~"),
    "10uF": ("Capacitor_SMD:C_0603_1608Metric", "C15849", "CL10A106KP8NNNC", "~"),
    "22uF": ("Capacitor_SMD:C_0805_2012Metric", "C45783", "CL21A226MAQNNNE", "~"),
    "LED_RED": ("LED_SMD:LED_0603_1608Metric", "C2286", "LTST-C190KRKT", "~"),
    "LED_GRN": ("LED_SMD:LED_0603_1608Metric", "C2297", "LTST-C190KGKT", "~"),
    "SW_PUSH": ("custom:Tactile-6x6-SMD", "C139797", "TS-1187A-B-A-B", "~"),
    "Conn_01x03": ("Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
                   "C49257", "KH-2.54PH180-1X3P-L13.5", "~"),
    "Conn_01x04": ("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
                   "C49258", "KH-2.54PH180-1X4P-L13.5", "~"),
    "Conn_01x05": ("Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
                   "C492404", "PZ254V-11-05P", "~"),
    "Conn_01x08": ("Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical",
                   "C492407", "PZ254V-11-08P", "~"),
    "ScrewTerm_2P": ("custom:ScrewTerm-5.08-2P", "C8465", "WJ500V-5.08-2P", "~"),
    "ScrewTerm_3P": ("custom:ScrewTerm-5.08-3P", "C8465", "WJ500V-5.08-3P", "~"),
}


def fp_of(board, value_key):
    return PARTS[value_key][0].replace("custom:", board + ":")


# ---------------------------------------------------------------------------
# Module pin tables (pad number -> pin name), from the official Espressif
# kicad-libraries symbols (cited above).  Pads not listed are NC.
# ---------------------------------------------------------------------------
H2_MINI_PINS = {
    "1": "GND", "2": "GND", "3": "3V3", "5": "GPIO2", "6": "GPIO3",
    "8": "EN", "11": "GND", "12": "GPIO13", "13": "GPIO14", "14": "GND",
    "15": "VBAT", "16": "GPIO12", "18": "GPIO4", "19": "GPIO5",
    "20": "GPIO10", "21": "GPIO11", "22": "GPIO8", "23": "GPIO9",
    "26": "GPIO26/USB_D-", "27": "GPIO27/USB_D+", "30": "GPIO23/U0RXD",
    "31": "GPIO24/U0TXD",
    "36": "GND", "37": "GND", "38": "GND", "39": "GND", "40": "GND",
    "41": "GND", "42": "GND", "43": "GND", "44": "GND", "45": "GND",
    "46": "GND", "47": "GND", "48": "GND", "49": "EP/GND", "50": "GND",
    "51": "GND", "52": "GND", "53": "GND",
}
S3_WROOM_PINS = {
    "1": "GND", "2": "3V3", "3": "EN", "4": "IO4", "5": "IO5", "6": "IO6",
    "7": "IO7", "8": "IO15", "9": "IO16", "10": "IO17", "11": "IO18",
    "12": "IO8", "13": "IO3", "14": "IO46", "15": "IO9", "16": "IO10",
    "17": "IO11", "18": "IO12", "19": "IO13", "20": "IO14", "21": "IO21",
    "22": "IO47", "23": "IO48", "24": "IO45", "25": "IO0", "26": "IO35*",
    "27": "IO36*", "28": "IO37*", "29": "IO38", "30": "IO39", "31": "IO40",
    "32": "IO41", "33": "IO42", "34": "RXD0/IO44", "35": "TXD0/IO43",
    "36": "IO2", "37": "IO1", "38": "GND", "39": "IO19/USB_D-",
    "40": "IO20/USB_D+", "41": "EP/GND",
}
C6_WROOM_PINS = {
    "1": "GND", "2": "3V3", "3": "EN", "4": "IO4", "5": "IO5", "6": "IO6",
    "7": "IO7", "8": "IO0", "9": "IO1", "10": "IO8", "11": "IO10",
    "12": "IO11", "13": "IO12/USB_D-", "14": "IO13/USB_D+", "15": "IO9",
    "16": "IO18", "17": "IO19", "18": "IO20", "19": "IO21", "20": "IO22",
    "21": "IO23", "22": "NC", "23": "IO15", "24": "RXD0/IO17",
    "25": "TXD0/IO16", "26": "IO3", "27": "IO2", "28": "GND", "29": "EP/GND",
}
C3_WROOM_PINS = {
    "1": "3V3", "2": "EN", "3": "IO4", "4": "IO5", "5": "IO6", "6": "IO7",
    "7": "IO8", "8": "IO9", "9": "GND", "10": "IO10", "11": "RXD0/IO20",
    "12": "TXD0/IO21", "13": "IO18/USB_D-", "14": "IO19/USB_D+",
    "15": "IO3", "16": "IO2", "17": "IO1", "18": "IO0", "19": "EP/GND",
}


# ---------------------------------------------------------------------------
# Custom inline footprints
# ---------------------------------------------------------------------------
def make_footprints(lib):
    """Return {name: Footprint} for every custom footprint used by wave-2."""
    fps = {}

    def box_outline(fp, hw, hh, cr=0.5):
        fp.add_rect(-hw, -hh, hw, hh, "F.Fab", 0.1)
        fp.add_rect(-hw - cr, -hh - cr, hw + cr, hh + cr, "F.CrtYd", 0.05)
        fp.add_line(-hw, -hh, hw, -hh, "F.SilkS")
        fp.add_line(-hw, hh, hw, hh, "F.SilkS")
        fp.add_line(-hw, -hh, -hw, -hh + 2, "F.SilkS")
        fp.add_line(hw, -hh, hw, -hh + 2, "F.SilkS")
        fp.add_line(-hw, hh - 2, -hw, hh, "F.SilkS")
        fp.add_line(hw, hh - 2, hw, hh, "F.SilkS")

    # --- ESP32-H2-MINI-1 (official land pattern; see module docstring) -----
    fp = kg.Footprint(lib, "ESP32-H2-MINI-1")
    for i in range(11):        # left column pads 1..11, top -> bottom
        fp.add_pad(str(1 + i), "smd", "rect", -5.9, -1.3 + i * 0.8, 0.8, 0.4)
    for i in range(13):        # bottom row pads 12..24, left -> right
        fp.add_pad(str(12 + i), "smd", "rect", -4.8 + i * 0.8, 7.6, 0.4, 0.8)
    for i in range(11):        # right column pads 25..35, bottom -> top
        fp.add_pad(str(25 + i), "smd", "rect", 5.9, 6.7 - i * 0.8, 0.8, 0.4)
    for i in range(13):        # top row pads 36..48, right -> left
        fp.add_pad(str(36 + i), "smd", "rect", 4.8 - i * 0.8, -2.2, 0.4, 0.8)
    fp.add_pad("49", "smd", "rect", 0.0, 2.7, 5.4, 5.4)          # EP (grid)
    for num, x, y in (("50", 5.95, -2.25), ("51", 5.95, 7.65),
                      ("52", -5.95, 7.65), ("53", -5.95, -2.25)):
        fp.add_pad(num, "smd", "rect", x, y, 0.7, 0.7)
    fp.add_rect(-6.6, -8.3, 6.6, 8.3, "F.Fab", 0.1)
    fp.add_rect(-7.1, -8.8, 7.1, 8.8, "F.CrtYd", 0.05)
    fp.add_line(-6.6, 8.3, 6.6, 8.3, "F.SilkS")
    fp.add_line(-6.6, 8.3, -6.6, 5.0, "F.SilkS")
    fp.add_line(6.6, 8.3, 6.6, 5.0, "F.SilkS")
    fp.add_line(-6.6, -8.3, 6.6, -8.3, "F.SilkS")
    fp.add_line(-6.6, -8.3, -6.6, -3.5, "F.SilkS")
    fp.add_line(6.6, -8.3, 6.6, -3.5, "F.SilkS")
    fps["ESP32-H2-MINI-1"] = fp

    # --- ESP32-S3-WROOM-1 (official land pattern) --------------------------
    fp = kg.Footprint(lib, "ESP32-S3-WROOM-1")
    for i in range(14):        # left column 1..14, top -> bottom
        fp.add_pad(str(1 + i), "smd", "rect", -8.75, -8.26 + i * 1.27, 1.5, 0.9)
    for i in range(12):        # bottom row 15..26, left -> right
        fp.add_pad(str(15 + i), "smd", "rect", -6.985 + i * 1.27, 9.5, 1.5, 0.9)
    for i in range(14):        # right column 27..40, bottom -> top
        fp.add_pad(str(27 + i), "smd", "rect", 8.75, 8.25 - i * 1.27, 1.5, 0.9)
    fp.add_pad("41", "smd", "rect", 0.0, 0.0, 5.8, 4.0)          # EP (grid)
    fp.add_rect(-9.0, -12.75, 9.0, 12.75, "F.Fab", 0.1)
    fp.add_rect(-9.5, -13.25, 9.5, 13.25, "F.CrtYd", 0.05)
    fp.add_line(-9.0, -12.75, 9.0, -12.75, "F.SilkS")
    fp.add_line(-9.0, -12.75, -9.0, -9.6, "F.SilkS")
    fp.add_line(9.0, -12.75, 9.0, -9.6, "F.SilkS")
    fp.add_line(-9.0, 11.0, -9.0, 12.75, "F.SilkS")
    fp.add_line(9.0, 11.0, 9.0, 12.75, "F.SilkS")
    fp.add_line(-9.0, 12.75, 9.0, 12.75, "F.SilkS")
    fps["ESP32-S3-WROOM-1"] = fp

    # --- ESP32-C6-WROOM-1 (official land pattern) --------------------------
    fp = kg.Footprint(lib, "ESP32-C6-WROOM-1")
    for i in range(14):
        fp.add_pad(str(1 + i), "smd", "rect", -8.75, -8.26 + i * 1.27, 1.5, 0.9)
    for i in range(14):
        fp.add_pad(str(15 + i), "smd", "rect", 8.75, 8.25 - i * 1.27, 1.5, 0.9)
    fp.add_pad("29", "smd", "rect", 0.0, 0.0, 7.5, 12.3)         # EP (grid)
    fp.add_rect(-9.0, -12.75, 9.0, 12.75, "F.Fab", 0.1)
    fp.add_rect(-9.5, -13.25, 9.5, 13.25, "F.CrtYd", 0.05)
    fp.add_line(-9.0, -12.75, 9.0, -12.75, "F.SilkS")
    fp.add_line(-9.0, -12.75, -9.0, -9.6, "F.SilkS")
    fp.add_line(9.0, -12.75, 9.0, -9.6, "F.SilkS")
    fp.add_line(-9.0, 9.6, -9.0, 12.75, "F.SilkS")
    fp.add_line(9.0, 9.6, 9.0, 12.75, "F.SilkS")
    fp.add_line(-9.0, 12.75, 9.0, 12.75, "F.SilkS")
    fps["ESP32-C6-WROOM-1"] = fp

    # --- ESP32-C3-WROOM-02 (official land pattern; 18.5 x 20 mm body) ------
    fp = kg.Footprint(lib, "ESP32-C3-WROOM-02")
    for i in range(9):
        fp.add_pad(str(1 + i), "smd", "rect", -8.75, -5.9 + i * 1.5, 1.5, 0.9)
    for i in range(9):
        fp.add_pad(str(10 + i), "smd", "rect", 8.75, 6.1 - i * 1.5, 1.5, 0.9)
    fp.add_pad("19", "smd", "rect", 0.96, 0.3, 3.3, 3.3)         # EP (grid)
    fp.add_rect(-9.25, -10.0, 9.25, 10.0, "F.Fab", 0.1)
    fp.add_rect(-9.75, -10.5, 9.75, 10.5, "F.CrtYd", 0.05)
    fp.add_line(-9.25, -10.0, 9.25, -10.0, "F.SilkS")
    fp.add_line(-9.25, -10.0, -9.25, -7.2, "F.SilkS")
    fp.add_line(9.25, -10.0, 9.25, -7.2, "F.SilkS")
    fp.add_line(-9.25, 7.5, -9.25, 10.0, "F.SilkS")
    fp.add_line(9.25, 7.5, 9.25, 10.0, "F.SilkS")
    fp.add_line(-9.25, 10.0, 9.25, 10.0, "F.SilkS")
    fps["ESP32-C3-WROOM-02"] = fp

    # --- Tactile 6x6 SMD ----------------------------------------------------
    fp = kg.Footprint(lib, "Tactile-6x6-SMD")
    for num, x, y in (("1", -4.5, -2.25), ("2", 4.5, -2.25),
                      ("3", -4.5, 2.25), ("4", 4.5, 2.25)):
        fp.add_pad(num, "smd", "rect", x, y, 2.3, 1.5)
    fp.add_rect(-3.0, -3.0, 3.0, 3.0, "F.Fab", 0.1)
    fp.add_rect(-5.95, -3.15, 5.95, 3.15, "F.CrtYd", 0.05)
    fp.add_rect(-3.0, -3.0, 3.0, 3.0, "F.SilkS", 0.12)
    fps["Tactile-6x6-SMD"] = fp

    # --- SHT31 DFN-8 (as sensenode-c6) --------------------------------------
    fp = kg.Footprint(lib, "SHT31-DFN8")
    for i, y in enumerate((-1.2, -0.4, 0.4, 1.2)):
        fp.add_pad(str(i + 1), "smd", "rect", -1.05, y, 0.5, 0.3)
    for i, y in enumerate((1.2, 0.4, -0.4, -1.2)):
        fp.add_pad(str(8 - i), "smd", "rect", 1.05, y, 0.5, 0.3)
    fp.add_pad("9", "smd", "rect", 0.0, 0.0, 1.4, 1.0)
    box_outline(fp, 1.25, 1.25)
    fps["SHT31-DFN8"] = fp

    # --- BH1750 WSOF-6I (as sensenode-c6) ------------------------------------
    fp = kg.Footprint(lib, "BH1750-WSOF6")
    for i, y in enumerate((-0.95, 0.0, 0.95)):   # WSOF-6I: 0.95 mm pitch
        fp.add_pad(str(i + 1), "smd", "rect", -1.43, y, 0.85, 0.4)
    for i, y in enumerate((0.95, 0.0, -0.95)):
        fp.add_pad(str(6 - i), "smd", "rect", 1.43, y, 0.85, 0.4)
    fp.add_pad("7", "smd", "rect", 0.0, 0.0, 1.5, 1.2)
    box_outline(fp, 1.6, 1.45, 0.25)
    fps["BH1750-WSOF6"] = fp

    # --- SHT40 DFN-4 (1.5x1.5, pitch 0.8; 1=SDA 2=SCL 3=VDD 4=VSS) ---------
    fp = kg.Footprint(lib, "SHT40-DFN4")
    fp.add_pad("1", "smd", "rect", -0.55, -0.4, 0.4, 0.5)
    fp.add_pad("2", "smd", "rect", -0.55, 0.4, 0.4, 0.5)
    fp.add_pad("3", "smd", "rect", 0.55, 0.4, 0.4, 0.5)
    fp.add_pad("4", "smd", "rect", 0.55, -0.4, 0.4, 0.5)
    box_outline(fp, 0.75, 0.75, 0.3)
    fp.add_circle(-1.2, -0.9, 0.2, "F.SilkS")
    fps["SHT40-DFN4"] = fp

    # --- SGP40 DFN-6 (2.44x2.44; 1=VDD 2=VSS 3=SDA 4=NC 5=VDDH 6=SCL) -----
    fp = kg.Footprint(lib, "SGP40-DFN6")
    for i, y in enumerate((-0.65, 0.0, 0.65)):
        fp.add_pad(str(1 + i), "smd", "rect", -1.0, y, 0.6, 0.35)
    for i, y in enumerate((0.65, 0.0, -0.65)):
        fp.add_pad(str(6 - i), "smd", "rect", 1.0, y, 0.6, 0.35)
    box_outline(fp, 1.22, 1.22, 0.3)
    fp.add_circle(-1.5, -1.1, 0.2, "F.SilkS")
    fps["SGP40-DFN6"] = fp

    # --- SCD40 (10.1x10.1; 1=SCL 2=GND 3=VDD 4=SDA) — simplified pads -----
    fp = kg.Footprint(lib, "SCD40")
    for num, x, y in (("1", -2.5, -1.5), ("2", -2.5, 1.5),
                      ("3", 2.5, 1.5), ("4", 2.5, -1.5)):
        fp.add_pad(num, "smd", "rect", x, y, 1.4, 1.4)
    fp.add_rect(-5.05, -5.05, 5.05, 5.05, "F.Fab", 0.1)
    fp.add_rect(-5.6, -5.6, 5.6, 5.6, "F.CrtYd", 0.05)
    fp.add_rect(-5.05, -5.05, 5.05, 5.05, "F.SilkS", 0.12)
    fp.add_circle(-3.5, -3.9, 0.3, "F.SilkS")
    fp.add_text("CO2", 0, 0)
    fps["SCD40"] = fp

    # --- CR2032 SMD holder (BS-02 style; verify before fabrication) --------
    fp = kg.Footprint(lib, "CR2032-holder")
    fp.add_pad("1", "smd", "rect", -8.0, 0.0, 3.0, 3.5)   # BAT+ tab
    fp.add_pad("2", "smd", "rect", 8.0, 0.0, 3.0, 3.5)    # GND spring
    fp.add_circle(0, 0, 10.6, "F.SilkS")
    fp.add_circle(0, 0, 11.4, "F.CrtYd", 0.05)
    fp.add_circle(0, 0, 10.3, "F.Fab", 0.1)
    fp.add_text("CR2032", 0, 0)
    fp.add_text("+", -8.0, -3.2)
    fps["CR2032-holder"] = fp

    # --- JST-PH 2-pin top entry (B2B-PH-K-S), 2.0 mm pitch -----------------
    fp = kg.Footprint(lib, "JST-PH-2")
    fp.add_pad("1", "thru_hole", "rect", 0.0, 0.0, 1.5, 1.5,
               layers=("*.Cu", "*.Mask"), drill=0.75)
    fp.add_pad("2", "thru_hole", "circle", 2.0, 0.0, 1.5, 1.5,
               layers=("*.Cu", "*.Mask"), drill=0.75)
    fp.add_rect(-1.7, -2.4, 3.7, 2.0, "F.Fab", 0.1)
    fp.add_rect(-2.0, -2.7, 4.0, 2.3, "F.CrtYd", 0.05)
    fp.add_rect(-1.7, -2.4, 3.7, 2.0, "F.SilkS", 0.12)
    fp.add_text("+", -1.2, 1.0, size=0.8)
    fps["JST-PH-2"] = fp

    # --- 5.08 mm screw terminals --------------------------------------------
    for n in (2, 3):
        fp = kg.Footprint(lib, f"ScrewTerm-5.08-{n}P")
        for i in range(n):
            fp.add_pad(str(i + 1), "thru_hole",
                       "rect" if i == 0 else "circle", i * 5.08, 0.0,
                       2.4, 2.4, layers=("*.Cu", "*.Mask"), drill=1.3)
        fp.add_rect(-2.0, -3.8, (n - 1) * 5.08 + 2.0, 3.8, "F.Fab", 0.1)
        fp.add_rect(-2.3, -4.1, (n - 1) * 5.08 + 2.3, 4.1, "F.CrtYd", 0.05)
        fp.add_rect(-2.0, -3.8, (n - 1) * 5.08 + 2.0, 3.8, "F.SilkS", 0.12)
        fps[f"ScrewTerm-5.08-{n}P"] = fp

    # --- Reed switch SMD (Littelfuse 59170 style, ~7 mm body) --------------
    fp = kg.Footprint(lib, "Reed-SMD")
    fp.add_pad("1", "smd", "rect", -2.6, 0.0, 2.6, 1.4)
    fp.add_pad("2", "smd", "rect", 2.6, 0.0, 2.6, 1.4)
    box_outline(fp, 3.3, 1.0, 0.5)
    fps["Reed-SMD"] = fp

    # --- TSOP38238 IR receiver (THT, 2.54 pitch; 1=OUT 2=GND 3=VS) ---------
    fp = kg.Footprint(lib, "TSOP38238")
    for i in range(3):
        fp.add_pad(str(i + 1), "thru_hole",
                   "rect" if i == 0 else "circle", i * 2.54, 0.0, 1.6, 1.6,
                   layers=("*.Cu", "*.Mask"), drill=0.9)
    fp.add_rect(-1.5, -4.0, 6.58, 0.8, "F.Fab", 0.1)
    fp.add_rect(-1.8, -4.3, 6.88, 1.1, "F.CrtYd", 0.05)
    fp.add_rect(-1.5, -4.0, 6.58, 0.8, "F.SilkS", 0.12)
    fp.add_text("OUT GND VS", 2.54, 1.8, size=0.8)
    fps["TSOP38238"] = fp

    # --- 5 mm IR LED (THT) ---------------------------------------------------
    fp = kg.Footprint(lib, "IR-LED-5mm")
    fp.add_pad("1", "thru_hole", "rect", 0.0, 0.0, 1.6, 1.6,
               layers=("*.Cu", "*.Mask"), drill=0.9)   # anode
    fp.add_pad("2", "thru_hole", "circle", 2.54, 0.0, 1.6, 1.6,
               layers=("*.Cu", "*.Mask"), drill=0.9)  # cathode
    fp.add_circle(1.27, 0, 2.6, "F.SilkS")
    fp.add_circle(1.27, 0, 2.9, "F.CrtYd", 0.05)
    fp.add_line(-1.3, -3.1, 3.8, -3.1, "F.SilkS")       # flat side marker
    fps["IR-LED-5mm"] = fp

    # --- 4x4 mm SMD inductor (4.7uH) -----------------------------------------
    fp = kg.Footprint(lib, "IND-4040")
    fp.add_pad("1", "smd", "rect", -1.7, 0.0, 1.2, 3.6)
    fp.add_pad("2", "smd", "rect", 1.7, 0.0, 1.2, 3.6)
    box_outline(fp, 2.0, 2.0, 0.3)
    fps["IND-4040"] = fp

    # --- Capacitive soil-probe electrodes (B.Cu copper area at board tip) ---
    fp = kg.Footprint(lib, "SoilProbe-BCu")
    fp.add_pad("1", "smd", "rect", 0.0, -5.0, 18.0, 8.0, layers=("B.Cu",))
    fp.add_pad("2", "smd", "rect", 0.0, 5.0, 18.0, 8.0, layers=("B.Cu",))
    fp.add_rect(-9.0, -9.0, 9.0, 9.0, "B.CrtYd", 0.05)
    fp.add_line(-9.0, -9.0, 9.0, -9.0, "B.SilkS")
    fp.add_line(-9.0, 9.0, 9.0, 9.0, "B.SilkS")
    fp.add_text("SOIL", 0, 0, layer="B.SilkS")
    fps["SoilProbe-BCu"] = fp

    # --- TMC2209 socket marker (two 1x08 headers are placed separately) -----
    return fps


# ---------------------------------------------------------------------------
# Schematic machinery
# ---------------------------------------------------------------------------
def build_schematic(board, comps, powers=("GND", "+3V3")):
    """comps: list of dicts:
      {sym, ref, x, y, plan {pinnum: net|None}, value(optional)}
    Symbol defs come from spec SYMBOLS via add_symbols()."""
    lib = kg.SymbolLib(board + "-lib")
    for p in dict.fromkeys(powers):
        lib.add_power_symbol(p)
    add_symbols(board, lib, comps)
    sch = kg.Schematic(board, lib)
    for c in comps:
        sch.place(c["sym"], c["ref"], c["x"], c["y"], rot=c.get("rot", 0),
                  value=c.get("value", c["sym"]))
        for num, net in c["plan"].items():
            pt = sch.pin_at(c["ref"], num)
            if net is None:
                sch.no_connect(round(pt[0], 2), round(pt[1], 2))
            else:
                sch.label(net, round(pt[0], 2), round(pt[1], 2))
    for i, name in enumerate(powers):
        x, y = 15 + 10 * i, 25
        sch.place_power(name, x, y)
        sch.label(name, x, y)
    sch.sheet_note("v0.1 concept design -- verify before fabrication")
    return lib, sch


def add_symbols(board, lib, comps):
    """Define every symbol used by comps.  Each comp carries its own pin
    list in comp['pins'] as [(num, name, type), ...] (auto-sided)."""
    done = set()
    for c in comps:
        name = c["sym"]
        if name in done:
            continue
        done.add(name)
        pins = c["pins"]
        half = (len(pins) + 1) // 2
        plist = [(num, pname, ptype, "left" if i < half else "right")
                 for i, (num, pname, ptype) in enumerate(pins)]
        vkey = c.get("value", name)
        info = PARTS.get(vkey, ("", "", "", "~"))
        fp = c.get("footprint") or fp_of(board, vkey)
        lib.add_box_symbol(name, c["refp"], plist, footprint=fp,
                           datasheet=info[3] or "~", lcsc=info[1])


def std2(name):  # 2-pin passive pin list
    return [("1", "1", "passive"), ("2", "2", "passive")]


def module_comp(sym, ref, x, y, pin_names, plan, board):
    pins = [(n, pin_names.get(n, "NC"), "passive") for n in
            sorted(plan.keys() | pin_names.keys(), key=lambda s: int(s))]
    full_plan = {n: plan.get(n) for n, _nm, _t in pins}
    return {"sym": sym, "ref": ref, "x": x, "y": y, "refp": "U",
            "pins": pins, "plan": full_plan}


# ---------------------------------------------------------------------------
# PCB builder with geometric self-check (adapted from sensenode-c6)
# ---------------------------------------------------------------------------
CLEAR = 0.15
EDGE_CLEAR = 0.4
VIA_R = 0.4


def rot_pt(x, y, deg):
    r = math.radians(deg)
    c, s = round(math.cos(r)), round(math.sin(r))
    return x * c - y * s, x * s + y * c


def _pt_seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def _seg_seg_dist(a1, a2, b1, b2):
    def ccw(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    d1, d2 = ccw(b1, b2, a1), ccw(b1, b2, a2)
    d3, d4 = ccw(a1, a2, b1), ccw(a1, a2, b2)
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


class Board:
    def __init__(self, name, w, h, mounting=True):
        self.name, self.W, self.H = name, w, h
        self.pcb = kg.PCB(name)
        self.pcb.set_outline(w, h)
        self.pads = []    # (net, layers, x, y, hx, hy, ref, num)
        self.segs = []    # (net, layer, x1, y1, x2, y2, halfw)
        self.vias = []    # (net, x, y)
        self.crtyds = []  # (ref, x0, y0, x1, y1)
        self.pad_xy = {}
        self.keepouts = []
        if mounting is True:
            mounting = [(3.5, 3.5), (w - 3.5, 3.5), (3.5, h - 3.5),
                        (w - 3.5, h - 3.5)]
        self._mh = 0
        self.pcb.net("GND")
        for (mx, my) in (mounting or []):
            self.mount(mx, my)

    def mount(self, mx, my):
        self._mh += 1
        fp = kg.Footprint(self.pcb.lib_prefix, "MountingHole_M2.5")
        fp.add_pad("", "np_thru_hole", "circle", 0, 0, 3.2, 3.2,
                   layers=("*.Cu", "*.Mask"), drill=2.7, net="GND")
        fp.add_circle(0, 0, 2.6, "F.CrtYd", 0.05)
        self.pcb.add_footprint(fp, f"H{self._mh}", "MountingHole_M2.5", mx, my)
        self.pads.append(("GND", frozenset({"F.Cu", "B.Cu"}),
                          mx, my, 1.6, 1.6, "MH", ""))

    def place(self, fp, ref, value, x, y, rot=0, crtyd=None):
        self.pcb.add_footprint(fp, ref, value, x, y, rot)
        fobj = self.pcb._footprints[-1]["fp"]
        for p in fobj.pads:
            dx, dy = rot_pt(p["x"], p["y"], rot)
            ax, ay = x + dx, y + dy
            sx, sy = (p["sy"], p["sx"]) if rot % 180 else (p["sx"], p["sy"])
            layers = set(p["layers"])
            if "*.Cu" in layers:
                layers |= {"F.Cu", "B.Cu"}
            self.pad_xy[(ref, p["num"])] = (round(ax, 3), round(ay, 3))
            self.pads.append((p["net"], frozenset(layers), ax, ay,
                              sx / 2, sy / 2, ref, p["num"]))
        if crtyd:
            pts = [rot_pt(*pt, rot) for pt in
                   ((crtyd[0], crtyd[1]), (crtyd[2], crtyd[1]),
                    (crtyd[2], crtyd[3]), (crtyd[0], crtyd[3]))]
            xs = [p[0] + x for p in pts]
            ys = [p[1] + y for p in pts]
            self.crtyds.append((ref, min(xs), min(ys), max(xs), max(ys)))
        return fobj

    def assign(self, plans):
        """plans: {ref: {pad: net|None}}; mirrors nets into the copper model."""
        for ref, plan in plans.items():
            for pad, net in plan.items():
                if net:
                    self.pcb.set_pad_net(ref, pad, net)
        for i, (net, layers, x, y, hx, hy, ref, num) in enumerate(self.pads):
            if ref in ("MH",):
                continue
            n = plans.get(ref, {}).get(num)
            if n:
                self.pads[i] = (n, layers, x, y, hx, hy, ref, num)

    def P(self, ref, pad):
        return self.pad_xy[(ref, str(pad))]

    def route(self, net, pts, width=0.5, layer="F.Cu"):
        self.pcb.route(net, pts, layer=layer, width=width)
        for a, b in zip(pts, pts[1:]):
            if a != b:
                self.segs.append((net, layer, a[0], a[1], b[0], b[1],
                                  width / 2))

    def via(self, net, x, y):
        self.pcb.via(net, x, y)
        self.vias.append((net, float(x), float(y)))

    def keepout(self, x1, y1, x2, y2, note=""):
        self.pcb.keepout_rect(x1, y1, x2, y2, note=note)
        self.keepouts.append((x1, y1, x2, y2))

    # -- clearance probes used by the auto GND stitcher -----------------------
    def _via_ok(self, x, y, net="GND", margin=0.20):
        for n, layers, px, py, hx, hy, ref, num in self.pads:
            if n == net or ref == "MH":
                continue
            if _pt_rect_dist(x, y, px, py, hx, hy) - VIA_R < margin:
                return False
        for n, x2, y2 in self.vias:
            if n != net and math.hypot(x - x2, y - y2) - 2 * VIA_R < margin:
                return False
        for n, layer, x1, y1, x2, y2, hw in self.segs:
            if n == net:
                continue
            if _pt_seg_dist(x, y, x1, y1, x2, y2) - hw - VIA_R < margin:
                return False
        d_edge = min(x, self.W - x, y, self.H - y)
        if d_edge - VIA_R < EDGE_CLEAR:
            return False
        for kx0, ky0, kx1, ky1 in self.keepouts:
            if kx0 - VIA_R < x < kx1 + VIA_R and ky0 - VIA_R < y < ky1 + VIA_R:
                return False
        return True

    def _stub_ok(self, net, a, b):
        for n, layers, px, py, hx, hy, ref, num in self.pads:
            if n == net or ref == "MH":
                continue
            if "F.Cu" not in layers:
                continue
            if _seg_rect_dist(a[0], a[1], b[0], b[1], px, py, hx, hy) - 0.25 < 0.20:
                return False
        for n, layer, x1, y1, x2, y2, hw in self.segs:
            if n == net or layer != "F.Cu":
                continue
            if _seg_seg_dist(a, b, (x1, y1), (x2, y2)) - hw - 0.25 < 0.20:
                return False
        return True

    def gnd_stitch(self):
        """Every F.Cu-only SMD GND pad gets a short stub + via to the B.Cu
        GND pour.  THT pads (*.Cu) are tied by the pour directly."""
        placed = 0
        for n, layers, x, y, hx, hy, ref, num in list(self.pads):
            if n != "GND" or ref == "MH" or "B.Cu" in layers:
                continue
            if "F.Cu" not in layers:
                continue
            if hx >= 0.45 and hy >= 0.45 and self._via_ok(x, y):
                self.via("GND", x, y)   # via-in-pad (concept boards)
                placed += 1
                continue
            for dx, dy in ((0, hy + 1.3), (0, -(hy + 1.3)),
                           (hx + 1.3, 0), (-(hx + 1.3), 0),
                           (0, hy + 2.1), (0, -(hy + 2.1)),
                           (hx + 2.1, 0), (-(hx + 2.1), 0)):
                vx, vy = round(x + dx, 2), round(y + dy, 2)
                if self._via_ok(vx, vy) and self._stub_ok("GND", (x, y), (vx, vy)):
                    self.route("GND", [(x, y), (vx, vy)], width=0.5)
                    self.via("GND", vx, vy)
                    placed += 1
                    break
        return placed

    # -- full geometric self-check ----------------------------------------------
    def check(self):
        prob = []
        pads, segs, vias = self.pads, self.segs, self.vias
        for i, p1 in enumerate(pads):
            for p2 in pads[i + 1:]:
                if p1[0] == p2[0] or (p1[6] == p2[6]):
                    continue
                if not (p1[1] & p2[1]):
                    continue
                dx = abs(p1[2] - p2[2]) - p1[4] - p2[4]
                dy = abs(p1[3] - p2[3]) - p1[5] - p2[5]
                if dx < 0.10 and dy < 0.10:
                    prob.append(f"pad-pad {p1[6]}.{p1[7]}/{p2[6]}.{p2[7]} "
                                f"dx={dx:.2f} dy={dy:.2f}")
        for net, layer, x1, y1, x2, y2, hw in segs:
            for p in pads:
                if p[0] == net and p[0] is not None:
                    continue
                if layer not in p[1]:
                    continue
                d = _seg_rect_dist(x1, y1, x2, y2, p[2], p[3], p[4], p[5]) - hw
                if d < CLEAR - 1e-9:
                    prob.append(f"pad-seg {p[0]}/{net} d={d:.3f} pad {p[6]}.{p[7]}"
                                f"({p[2]:.2f},{p[3]:.2f}) seg({x1:.2f},{y1:.2f})-({x2:.2f},{y2:.2f})")
            for (vn, vx, vy) in vias:
                if vn == net:
                    continue
                d = _pt_seg_dist(vx, vy, x1, y1, x2, y2) - hw - VIA_R
                if d < CLEAR + 0.05:
                    prob.append(f"via-seg {vn}/{net} d={d:.3f} "
                                f"via({vx:.2f},{vy:.2f}) seg({x1:.2f},{y1:.2f})-({x2:.2f},{y2:.2f})")
        for i, s1 in enumerate(segs):
            for s2 in segs[i + 1:]:
                if s1[0] == s2[0] or s1[1] != s2[1]:
                    continue
                d = _seg_seg_dist((s1[2], s1[3]), (s1[4], s1[5]),
                                  (s2[2], s2[3]), (s2[4], s2[5])) - s1[6] - s2[6]
                if d < CLEAR - 1e-9:
                    prob.append(f"seg-seg {s1[0]}/{s2[0]} d={d:.3f} "
                                f"({s1[2]:.2f},{s1[3]:.2f})-({s1[4]:.2f},{s1[5]:.2f})")
        for i, v1 in enumerate(vias):
            for p in pads:
                if p[0] == v1[0] and p[0] is not None:
                    continue
                d = _pt_rect_dist(v1[1], v1[2], p[2], p[3], p[4], p[5]) - VIA_R
                if d < CLEAR - 1e-9:
                    prob.append(f"via-pad {v1[0]}/{p[0]} d={d:.3f} "
                                f"via({v1[1]:.2f},{v1[2]:.2f}) pad {p[6]}.{p[7]}")
            for v2 in vias[i + 1:]:
                if v1[0] == v2[0]:
                    continue
                if math.hypot(v1[1] - v2[1], v1[2] - v2[2]) - 2 * VIA_R < CLEAR - 1e-9:
                    prob.append(f"via-via {v1[0]}/{v2[0]}")
        for net, layer, xa, ya, xb, yb, hw in segs:
            for (ex, ey) in ((xa, ya), (xb, yb)):
                d_edge = min(ex, self.W - ex, ey, self.H - ey)
                if d_edge - hw < EDGE_CLEAR - 1e-9:
                    prob.append(f"edge-seg {net} @({ex:.2f},{ey:.2f})")
        for kx0, ky0, kx1, ky1 in self.keepouts:
            for net, layer, xa, ya, xb, yb, hw in segs:
                d = _seg_rect_dist(xa, ya, xb, yb, (kx0 + kx1) / 2, (ky0 + ky1) / 2,
                                   (kx1 - kx0) / 2, (ky1 - ky0) / 2) - hw
                if d < 0:
                    prob.append(f"keepout-seg {net} ({xa:.2f},{ya:.2f})-"
                                f"({xb:.2f},{yb:.2f})")
            for vn, vx, vy in vias:
                if kx0 - VIA_R < vx < kx1 + VIA_R and ky0 - VIA_R < vy < ky1 + VIA_R:
                    prob.append(f"keepout-via {vn} @({vx:.2f},{vy:.2f})")
        return prob


def finish_pcb(b, out_dir, extra_silk=None, zones=()):
    b.pcb.gnd_zone("B.Cu")
    for net, rect, layer in zones:
        b.pcb.zone(net, rect, layer=layer)
    b.pcb.silk_text(b.name, b.W / 2, 1.6, size=1.4)
    b.pcb.silk_text("v0.1 concept - MIT", b.W / 2, b.H - 1.6, size=1.0)
    for txt, x, y in (extra_silk or []):
        b.pcb.silk_text(txt, x, y, size=1.0)
    path = os.path.join(out_dir, b.name + ".kicad_pcb")
    b.pcb.save(path)
    probs = b.check()
    if probs:
        for p in probs:
            print("SELF-CHECK:", p)
        raise SystemExit(f"{b.name}: self-check failed ({len(probs)})")
    return path


def write_bom(board, out_dir, rows):
    """rows: [(refs_csv, value_key, qty)]"""
    with open(os.path.join(out_dir, "bom_lcsc.csv"), "w") as f:
        f.write("ref,value,footprint,lcsc,mpn,qty\n")
        for refs, vkey, qty in rows:
            fp, lcsc, mpn, _ds = PARTS[vkey]
            f.write(f"{refs},{vkey},{fp_of(board, vkey)},{lcsc},{mpn},{qty}\n")




# ---------------------------------------------------------------------------
# Board: threadnode-h2 (40 x 30) -- battery Thread contact sensor / button
# ---------------------------------------------------------------------------
def build_threadnode_h2():
    B = "threadnode-h2"
    out = os.path.join(BOARDS_ROOT, B)
    os.makedirs(out, exist_ok=True)
    fps = make_footprints(B)
    kg.write_project(os.path.join(out, B + ".kicad_pro"), B, B + "-lib")

    u1plan = {"1": "GND", "2": "GND", "3": "+3V3", "6": "REED", "8": "EN",
              "11": "GND", "12": "I2C_SCL", "14": "GND", "16": "I2C_SDA",
              "22": "STAT_LED", "23": "BTN", "30": "RX0", "31": "TX0",
              "36": "GND", "37": "GND", "38": "GND", "39": "GND", "40": "GND",
              "41": "GND", "42": "GND", "43": "GND", "44": "GND", "45": "GND",
              "46": "GND", "47": "GND", "48": "GND", "49": "GND", "50": "GND",
              "51": "GND", "52": "GND", "53": "GND"}
    comps = [
        module_comp("ESP32-H2-MINI-1", "U1", 100, 85, H2_MINI_PINS, u1plan, B),
        {"sym": "CR2032_HOLDER", "ref": "BT1", "x": 170, "y": 85, "refp": "BT",
         "pins": [("1", "+", "passive"), ("2", "-", "passive")],
         "plan": {"1": "+3V3", "2": "GND"}},
        {"sym": "REED", "ref": "SW1", "x": 145, "y": 130, "refp": "SW",
         "pins": std2("REED"), "plan": {"1": "REED", "2": "GND"}},
        {"sym": "SW_PUSH", "ref": "BT2", "x": 200, "y": 130, "refp": "BT",
         "pins": [("1", "A1", "passive"), ("2", "A2", "passive"),
                  ("3", "B1", "passive"), ("4", "B2", "passive")],
         "plan": {"1": "BTN", "2": "GND", "3": "BTN", "4": "GND"}},
        {"sym": "LED_GRN", "ref": "D1", "x": 235, "y": 85, "refp": "D",
         "pins": [("1", "A", "passive"), ("2", "K", "passive")],
         "plan": {"1": "LED1_A", "2": "STAT_LED"}},
        {"sym": "1k", "ref": "R1", "x": 235, "y": 65, "refp": "R",
         "pins": std2("1k"), "plan": {"1": "LED1_A", "2": "+3V3"}},
        {"sym": "10k", "ref": "R2", "x": 235, "y": 45, "refp": "R",
         "pins": std2("10k"), "plan": {"1": "+3V3", "2": "EN"}},
        {"sym": "100k", "ref": "R3", "x": 255, "y": 45, "refp": "R",
         "pins": std2("100k"), "plan": {"1": "+3V3", "2": "REED"}},
        {"sym": "4.7k", "ref": "R4", "x": 255, "y": 65, "refp": "R",
         "pins": std2("4.7k"), "plan": {"1": "I2C_SDA", "2": "+3V3"}},
        {"sym": "4.7k", "ref": "R5", "x": 255, "y": 85, "refp": "R",
         "pins": std2("4.7k"), "plan": {"1": "I2C_SCL", "2": "+3V3"}},
        {"sym": "10uF", "ref": "C1", "x": 235, "y": 105, "refp": "C",
         "pins": std2("10uF"), "plan": {"1": "+3V3", "2": "GND"}},
        {"sym": "100nF", "ref": "C2", "x": 255, "y": 105, "refp": "C",
         "pins": std2("100nF"), "plan": {"1": "+3V3", "2": "GND"}},
        {"sym": "100nF", "ref": "C3", "x": 235, "y": 125, "refp": "C",
         "pins": std2("100nF"), "plan": {"1": "EN", "2": "GND"}},
        {"sym": "Conn_01x04", "ref": "J1", "x": 145, "y": 160, "refp": "J",
         "pins": [("1", "3V3", "passive"), ("2", "TX0", "passive"),
                  ("3", "RX0", "passive"), ("4", "GND", "passive")],
         "plan": {"1": "+3V3", "2": "TX0", "3": "RX0", "4": "GND"}},
        {"sym": "Conn_01x04", "ref": "J2", "x": 200, "y": 160, "refp": "J",
         "pins": [("1", "3V3", "passive"), ("2", "SDA", "passive"),
                  ("3", "SCL", "passive"), ("4", "GND", "passive")],
         "plan": {"1": "+3V3", "2": "I2C_SDA", "3": "I2C_SCL", "4": "GND"}},
    ]
    lib, sch = build_schematic(B, comps, powers=("GND", "+3V3"))
    lib.save(os.path.join(out, B + "-lib.kicad_sym"))
    sch.save(os.path.join(out, B + ".kicad_sch"))

    # ---------------- PCB (40 x 30) ----------------
    b = Board(B, 40.0, 30.0, mounting=[(3.5, 3.5), (36.5, 3.5), (36.5, 26.5)])
    b.keepout(4.4, 0.2, 17.6, 5.6, "ANTENNA KEEP-OUT")
    RC = (-1.05, -0.65, 1.05, 0.65)
    b.place(fps["ESP32-H2-MINI-1"], "U1", "ESP32-H2-MINI-1", 11, 12)
    b.place(fps["CR2032-holder"], "BT1", "CR2032_HOLDER", 28.0, 15.0)
    b.place(fps["Reed-SMD"], "SW1", "REED", 3.6, 26.0, rot=90,
            crtyd=(-1.5, -3.8, 1.5, 3.8))
    b.place(fps["Tactile-6x6-SMD"], "BT2", "SW_PUSH", 34.0, 24.5,
            crtyd=(-5.95, -3.15, 5.95, 3.15))
    b.place("LED_SMD:LED_0603_1608Metric", "D1", "LED_GRN", 22.5, 19.5,
            rot=180, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R1", "1k", 25.5, 19.5, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R2", "10k", 19.5, 21.5, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R3", "100k", 27.0, 27.5, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R4", "4.7k", 19.0, 17.5, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R5", "4.7k", 20.5, 24.5,
            crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C1", "10uF", 9.0, 22.8, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C2", "100nF", 12.0, 22.8,
            crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C3", "100nF", 15.05, 12.5,
            crtyd=RC)
    b.place("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
            "J1", "Conn_01x04", 13.0, 27.6, rot=90)
    b.place("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
            "J2", "Conn_01x04", 22.5, 27.6, rot=90)

    plans = {c["ref"]: c["plan"] for c in comps}
    b.assign(plans)

    # ---- +3V3 rail (direct battery): holder -> trunk y=20.4 -> consumers ----
    b.route("+3V3", [b.P("BT1", "1"), (20.0, 20.4), (5.3, 20.4)])
    b.route("+3V3", [b.P("U1", "3"), (2.2, 12.3), (2.2, 20.4), (5.3, 20.4)])
    for ref in ("C1", "C2"):
        x, y = b.P(ref, "1")
        b.route("+3V3", [(x, y), (x, 20.4)])
    b.route("+3V3", [b.P("R2", "1"), (18.725, 20.4)])
    b.route("+3V3", [b.P("R4", "2"), (19.775, 20.4)])
    b.route("+3V3", [b.P("R5", "2"), (21.275, 20.4)])
    b.route("+3V3", [(20.0, 20.4), (26.275, 20.4)])
    b.route("+3V3", [b.P("R1", "2"), (26.275, 20.4)])
    # R3 + J1/J2 +3V3 pins
    b.route("+3V3", [b.P("R3", "1"), (26.225, 20.4)])
    b.route("+3V3", [b.P("J1", "1"), (13.0, 25.5), (11.7, 25.5), (11.7, 22.8),
                     (11.225, 22.8)])
    b.route("+3V3", [b.P("J2", "1"), (22.5, 24.5), (26.225, 24.5)])
    # LED anode link R1 p1 -> D1 p1
    b.route("LED1_A", [b.P("R1", "1"), b.P("D1", "1")], width=0.25)
    # EN: U1 p8 (5.1,16.3) -> via -> B.Cu -> C3 p1 / R2 p2
    b.route("EN", [b.P("U1", "8"), (4.2, 16.3)], width=0.25)
    b.via("EN", 4.2, 16.3)
    b.route("EN", [(4.2, 16.3), (14.9, 16.3), (14.9, 14.2)], layer="B.Cu",
            width=0.25)
    b.via("EN", 14.9, 14.2)
    b.route("EN", [(14.9, 14.2), (14.9, 13.2), (14.275, 13.2),
                   (14.275, 12.5)], width=0.25)
    b.route("EN", [(14.9, 16.3), (14.9, 23.0), (20.275, 23.0),
                   (20.275, 22.5)], layer="B.Cu", width=0.25)
    b.via("EN", 20.275, 22.5)
    b.route("EN", [(20.275, 22.5), b.P("R2", "2")], width=0.25)

    b.gnd_stitch()

    finish_pcb(b, out, extra_silk=[
        ("ThreadNode-H2", 28, 2.5), ("REED", 6.5, 24.0), ("BOOT", 34.0, 20.5),
        ("3V3 TX RX GND", 13.0, 25.4), ("3V3 SDA SCL GND", 22.5, 25.4)])
    write_bom(B, out, [
        ("U1", "ESP32-H2-MINI-1", 1), ("BT1", "CR2032_HOLDER", 1),
        ("SW1", "REED", 1), ("BT2", "SW_PUSH", 1), ("D1", "LED_GRN", 1),
        ("R1", "1k", 1), ("R2", "10k", 1), ("R3", "100k", 1),
        ("R4,R5", "4.7k", 2), ("C1", "10uF", 1), ("C2,C3", "100nF", 2),
        ("J1,J2", "Conn_01x04", 2)])
    problems = kg.validate_project(out)
    if problems:
        for p in problems:
            print("VALIDATE:", p)
        raise SystemExit(f"{B}: validate_project failed")
    print(f"{B}: OK")




# ---------------------------------------------------------------------------
# Shared USB-C power input block (pattern adapted from sensenode-c6):
# X1 USB-C 16P at board bottom edge, rot=180; VBUS/GND fanout zones on F.Cu,
# VBUS combined through vias onto a B.Cu trunk.
# ---------------------------------------------------------------------------
USB_X1_PLAN = {"1": "GND", "2": "VBUS", "3": "USB_CC1", "4": "USB_DP",
               "5": "USB_DM", "6": None, "7": "VBUS", "8": "GND",
               "9": "GND", "10": "VBUS", "11": None, "12": "USB_DM",
               "13": "USB_DP", "14": "USB_CC2", "15": "VBUS", "16": "GND",
               "S1": "GND", "S2": "GND", "S3": "GND", "S4": "GND"}
LDO_PLAN = {"1": "VBUS", "2": "GND", "3": "VBUS", "4": None, "5": "+3V3"}


def usb_cc_plans():
    return {"R3": {"1": "USB_CC1", "2": "GND"},
            "R4": {"1": "USB_CC2", "2": "GND"}}


def place_usbc(b, x0, H):
    """USB-C receptacle centered x0 at bottom edge + VBUS/GND fanout zones."""
    b.place("Connector_USB:USB_C_Receptacle_USB2.0_16P", "X1", "USB_C_16P",
            x0, H - 3.4, rot=180, crtyd=(-5.6, -2.2, 5.6, 4.4))
    y = H - 3.4
    b.pcb.zone("VBUS", (x0 - 3.7, y - 3.6, x0 - 0.55, y - 0.6), layer="F.Cu")
    b.pcb.zone("VBUS", (x0 + 0.55, y - 3.6, x0 + 3.35, y - 0.6), layer="F.Cu")
    b.pcb.zone("GND", (x0 - 5.1, y - 3.6, x0 - 3.45, y + 0.7), layer="F.Cu")
    b.pcb.zone("GND", (x0 - 0.45, y - 3.6, x0 + 0.45, y - 1.3), layer="F.Cu")
    b.pcb.zone("GND", (x0 + 3.45, y - 3.6, x0 + 5.1, y + 0.7), layer="F.Cu")


# ---------------------------------------------------------------------------
# Board: airquality-s3 (60 x 40) -- CO2 + VOC + temp/hum + OLED header
# ---------------------------------------------------------------------------
def build_airquality_s3():
    B = "airquality-s3"
    out = os.path.join(BOARDS_ROOT, B)
    os.makedirs(out, exist_ok=True)
    fps = make_footprints(B)
    kg.write_project(os.path.join(out, B + ".kicad_pro"), B, B + "-lib")

    u1plan = {"1": "GND", "2": "+3V3", "3": "EN", "12": "I2C_SDA",
              "15": "I2C_SCL", "25": "BOOT", "29": "STAT_LED",
              "34": "RX0", "35": "TX0", "38": "GND", "39": "USB_DM",
              "40": "USB_DP", "41": "GND"}
    comps = [
        module_comp("ESP32-S3-WROOM-1", "U1", 100, 85, S3_WROOM_PINS, u1plan, B),
        {"sym": "USB_C_16P", "ref": "X1", "x": 30, "y": 60, "refp": "X",
         "pins": [(str(i), n, "passive") for i, n in enumerate(
             ["GND1", "VBUS1", "CC1", "DP1", "DM1", "SBU1", "VBUS2", "GND2",
              "GND3", "VBUS3", "SBU2", "DM2", "DP2", "CC2", "VBUS4", "GND4"],
             1)] + [("S1", "SH1", "passive"), ("S2", "SH2", "passive"),
                    ("S3", "SH3", "passive"), ("S4", "SH4", "passive")],
         "plan": USB_X1_PLAN},
        {"sym": "AP2112K-3.3", "ref": "U2", "x": 60, "y": 90, "refp": "U",
         "pins": [("1", "VIN", "passive"), ("2", "GND", "passive"),
                  ("3", "EN", "passive"), ("4", "NC", "passive"),
                  ("5", "VOUT", "passive")], "plan": LDO_PLAN},
        {"sym": "SCD40", "ref": "U3", "x": 140, "y": 60, "refp": "U",
         "pins": [("1", "SCL", "passive"), ("2", "GND", "passive"),
                  ("3", "VDD", "passive"), ("4", "SDA", "passive")],
         "plan": {"1": "I2C_SCL", "2": "GND", "3": "+3V3", "4": "I2C_SDA"}},
        {"sym": "SGP40", "ref": "U4", "x": 140, "y": 90, "refp": "U",
         "pins": [("1", "VDD", "passive"), ("2", "VSS", "passive"),
                  ("3", "SDA", "passive"), ("4", "NC", "passive"),
                  ("5", "VDDH", "passive"), ("6", "SCL", "passive")],
         "plan": {"1": "+3V3", "2": "GND", "3": "I2C_SDA", "4": "GND",
                  "5": "+3V3", "6": "I2C_SCL"}},
        {"sym": "SHT40", "ref": "U5", "x": 140, "y": 115, "refp": "U",
         "pins": [("1", "SDA", "passive"), ("2", "SCL", "passive"),
                  ("3", "VDD", "passive"), ("4", "VSS", "passive")],
         "plan": {"1": "I2C_SDA", "2": "I2C_SCL", "3": "+3V3", "4": "GND"}},
        {"sym": "SW_PUSH", "ref": "BT1", "x": 30, "y": 115, "refp": "BT",
         "pins": [("1", "A1", "passive"), ("2", "A2", "passive"),
                  ("3", "B1", "passive"), ("4", "B2", "passive")],
         "plan": {"1": "EN", "2": "GND", "3": "EN", "4": "GND"}},
        {"sym": "SW_PUSH", "ref": "BT2", "x": 60, "y": 115, "refp": "BT",
         "pins": [("1", "A1", "passive"), ("2", "A2", "passive"),
                  ("3", "B1", "passive"), ("4", "B2", "passive")],
         "plan": {"1": "BOOT", "2": "GND", "3": "BOOT", "4": "GND"}},
        {"sym": "LED_GRN", "ref": "D1", "x": 175, "y": 60, "refp": "D",
         "pins": [("1", "A", "passive"), ("2", "K", "passive")],
         "plan": {"1": "LED1_A", "2": "STAT_LED"}},
        {"sym": "1k", "ref": "R8", "x": 175, "y": 40, "refp": "R",
         "pins": std2("1k"), "plan": {"1": "+3V3", "2": "LED1_A"}},
        {"sym": "5.1k", "ref": "R3", "x": 90, "y": 115, "refp": "R",
         "pins": std2("5.1k"), "plan": {"1": "USB_CC1", "2": "GND"}},
        {"sym": "5.1k", "ref": "R4", "x": 110, "y": 115, "refp": "R",
         "pins": std2("5.1k"), "plan": {"1": "USB_CC2", "2": "GND"}},
        {"sym": "10k", "ref": "R7", "x": 175, "y": 90, "refp": "R",
         "pins": std2("10k"), "plan": {"1": "+3V3", "2": "EN"}},
        {"sym": "4.7k", "ref": "R1", "x": 175, "y": 115, "refp": "R",
         "pins": std2("4.7k"), "plan": {"1": "+3V3", "2": "I2C_SDA"}},
        {"sym": "4.7k", "ref": "R2", "x": 195, "y": 115, "refp": "R",
         "pins": std2("4.7k"), "plan": {"1": "+3V3", "2": "I2C_SCL"}},
        {"sym": "10uF", "ref": "C1", "x": 90, "y": 140, "refp": "C",
         "pins": std2("10uF"), "plan": {"1": "VBUS", "2": "GND"}},
        {"sym": "10uF", "ref": "C2", "x": 110, "y": 140, "refp": "C",
         "pins": std2("10uF"), "plan": {"1": "+3V3", "2": "GND"}},
        {"sym": "100nF", "ref": "C3", "x": 130, "y": 140, "refp": "C",
         "pins": std2("100nF"), "plan": {"1": "+3V3", "2": "GND"}},
        {"sym": "100nF", "ref": "C4", "x": 150, "y": 140, "refp": "C",
         "pins": std2("100nF"), "plan": {"1": "+3V3", "2": "GND"}},
        {"sym": "Conn_01x04", "ref": "J1", "x": 90, "y": 165, "refp": "J",
         "pins": [("1", "3V3", "passive"), ("2", "TX0", "passive"),
                  ("3", "RX0", "passive"), ("4", "GND", "passive")],
         "plan": {"1": "+3V3", "2": "TX0", "3": "RX0", "4": "GND"}},
        {"sym": "Conn_01x04", "ref": "J2", "x": 145, "y": 165, "refp": "J",
         "pins": [("1", "3V3", "passive"), ("2", "SDA", "passive"),
                  ("3", "SCL", "passive"), ("4", "GND", "passive")],
         "plan": {"1": "+3V3", "2": "I2C_SDA", "3": "I2C_SCL", "4": "GND"}},
    ]
    lib, sch = build_schematic(B, comps, powers=("GND", "+3V3", "VBUS"))
    lib.save(os.path.join(out, B + "-lib.kicad_sym"))
    sch.save(os.path.join(out, B + ".kicad_sch"))

    # ---------------- PCB (60 x 40) ----------------
    b = Board(B, 60.0, 40.0)
    b.keepout(10.8, 0.2, 29.2, 4.2, "ANTENNA KEEP-OUT")
    RC = (-1.05, -0.65, 1.05, 0.65)
    b.place(fps["ESP32-S3-WROOM-1"], "U1", "ESP32-S3-WROOM-1", 20, 15)
    place_usbc(b, 44.0, 40.0)
    b.place("Package_TO_SOT_SMD:SOT-23-5", "U2", "AP2112K-3.3", 35, 30,
            crtyd=(-1.6, -1.75, 1.6, 1.75))
    b.place(fps["SCD40"], "U3", "SCD40", 48, 9, crtyd=(-5.6, -5.6, 5.6, 5.6))
    b.place(fps["SGP40-DFN6"], "U4", "SGP40", 47, 20,
            crtyd=(-1.6, -1.6, 1.6, 1.6))
    b.place(fps["SHT40-DFN4"], "U5", "SHT40", 53, 20,
            crtyd=(-1.1, -1.1, 1.1, 1.1))
    b.place(fps["Tactile-6x6-SMD"], "BT1", "SW_PUSH", 5.5, 14.6, rot=90,
            crtyd=(-3.15, -5.95, 3.15, 5.95))
    b.place(fps["Tactile-6x6-SMD"], "BT2", "SW_PUSH", 5.5, 26.2, rot=90,
            crtyd=(-3.15, -5.95, 3.15, 5.95))
    b.place("LED_SMD:LED_0603_1608Metric", "D1", "LED_GRN", 36, 6, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R8", "1k", 33, 6, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R3", "5.1k", 40, 30, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R4", "5.1k", 40, 32, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R7", "10k", 14, 12.5, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R1", "4.7k", 44, 14.5, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R2", "4.7k", 44, 17.5, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C1", "10uF", 30, 34.5,
            rot=180, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C2", "10uF", 33, 28,
            rot=180, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C3", "100nF", 8, 6, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C4", "100nF", 42, 9,
            rot=180, crtyd=RC)
    b.place("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
            "J1", "Conn_01x04", 5, 27)
    b.place("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
            "J2", "Conn_01x04", 55, 27)

    plans = {c["ref"]: c["plan"] for c in comps}
    b.assign(plans)

    # ---- VBUS: USB zones -> vias -> B.Cu combine -> LDO + C1 ----
    b.via("VBUS", 43.1, 35.5)
    b.via("VBUS", 47.1, 35.8)
    b.route("VBUS", [(43.1, 35.5), (47.1, 35.5), (47.1, 35.8)], layer="B.Cu",
            width=0.5)
    b.route("VBUS", [(47.1, 35.8), (47.1, 32.6), (32.6, 32.6)], layer="B.Cu",
            width=0.5)
    b.via("VBUS", 32.6, 32.6)
    b.route("VBUS", [(32.6, 32.6), (32.6, 29.05), (34.05, 29.05)])  # U2 EN p3
    b.route("VBUS", [(32.6, 30.95), (34.05, 30.95)])                # U2 VIN p1
    b.route("VBUS", [(32.6, 32.6), (30.775, 32.6)], layer="B.Cu", width=0.5)
    b.via("VBUS", 30.775, 32.6)
    b.route("VBUS", [(30.775, 32.6), (30.775, 34.5)])   # C1 p1
    # ---- +3V3: LDO VOUT -> trunk y=28.2 -> module + sensors ----
    b.route("+3V3", [(35.95, 29.525), (37.3, 29.525), (37.3, 28.2),
                     (33.775, 28.2)])
    b.route("+3V3", [(33.775, 28.2), (33.775, 28.0)])               # C2 p1
    b.route("+3V3", [(37.3, 28.2), (52.0, 28.2)])                   # trunk right
    b.route("+3V3", [(33.775, 28.2), (33.775, 26.8), (30.0, 26.8),
                     (30.0, 25.0)])                         # trunk left
    # module VDD: pin2 (11.25,8.01) exits left, B.Cu hop to trunk
    b.route("+3V3", [(11.25, 8.01), (9.2, 8.01)])
    b.via("+3V3", 9.2, 8.01)
    b.route("+3V3", [(7.225, 6.0), (7.225, 8.01), (9.2, 8.01)])     # C3 p1
    b.route("+3V3", [(9.2, 8.01), (9.2, 25.0)], layer="B.Cu", width=0.5)
    # sensor + pullup stubs down to trunk
    b.route("+3V3", [(50.5, 10.5), (50.5, 28.2)])                   # SCD40 VDD
    b.route("+3V3", [(46.0, 19.35), (45.2, 19.35), (45.2, 28.2)])   # SGP40 VDD
    b.route("+3V3", [(48.0, 20.0), (48.9, 20.0), (48.9, 28.2)])    # SGP40 VDDH p5
    b.route("+3V3", [(53.55, 20.4), (53.55, 28.2)])                 # SHT40 VDD
    b.route("+3V3", [(42.775, 9.0), (42.775, 28.2)])                # C4 p1
    b.route("+3V3", [(43.225, 14.5), (43.225, 28.2)])               # R1 p1
    b.route("+3V3", [(43.225, 17.5), (43.225, 15.7), (42.5, 15.7),
                     (42.5, 28.2)])                                  # R2 p1
    b.route("+3V3", [(55.0, 27.0), (52.6, 27.0), (52.6, 28.2)])     # J2 OLED p1
    b.route("+3V3", [(5.0, 27.0), (5.0, 25.0)], width=0.5)
    b.via("+3V3", 5.0, 25.0)
    b.route("+3V3", [(5.0, 25.0), (9.2, 25.0), (30.0, 25.0)], layer="B.Cu",
            width=0.5)
    b.via("+3V3", 30.0, 25.0)
    # R7 EN pull-up +3V3 (via B.Cu hop to the x=9.2 trunk)
    b.route("+3V3", [(13.225, 12.5), (13.225, 14.5)])
    b.via("+3V3", 13.225, 14.5)
    b.route("+3V3", [(13.225, 14.5), (9.2, 14.5)], layer="B.Cu", width=0.5)
    # LED: R8 p2 -> D1 p1 (signal LED1_A)
    b.route("LED1_A", [(33.775, 6.0), (35.225, 6.0)], width=0.25)

    b.gnd_stitch()
    finish_pcb(b, out, extra_silk=[
        ("AirQuality-S3", 45, 2.5), ("EN", 6.5, 12.2), ("BOOT", 6.5, 22.2),
        ("SCD40", 48, 14.8), ("OLED 3V3 SDA SCL GND", 55, 24.8),
        ("3V3 TX RX GND", 9.5, 27.0)])
    write_bom(B, out, [
        ("U1", "ESP32-S3-WROOM-1", 1), ("X1", "USB_C_16P", 1),
        ("U2", "AP2112K-3.3", 1), ("U3", "SCD40", 1), ("U4", "SGP40", 1),
        ("U5", "SHT40", 1), ("BT1,BT2", "SW_PUSH", 2), ("D1", "LED_GRN", 1),
        ("R1,R2", "4.7k", 2), ("R3,R4", "5.1k", 2), ("R7", "10k", 1),
        ("R8", "1k", 1), ("C1,C2", "10uF", 2), ("C3,C4", "100nF", 2),
        ("J1,J2", "Conn_01x04", 2)])
    problems = kg.validate_project(out)
    if problems:
        for p in problems:
            print("VALIDATE:", p)
        raise SystemExit(f"{B}: validate_project failed")
    print(f"{B}: OK")

# ---------------------------------------------------------------------------
# Board: blinddriver-c6 (70 x 50) -- TMC2209 stepper roller-blind controller
# ---------------------------------------------------------------------------
def build_blinddriver_c6():
    B = "blinddriver-c6"
    out = os.path.join(BOARDS_ROOT, B)
    os.makedirs(out, exist_ok=True)
    fps = make_footprints(B)
    kg.write_project(os.path.join(out, B + ".kicad_pro"), B, B + "-lib")

    u1plan = {"1": "GND", "2": "+3V3", "3": "EN", "4": "STEP", "5": "DIR",
              "6": "TMC_EN", "7": "DIAG", "8": "BOOT", "9": "STAT_LED",
              "13": "USB_DM", "14": "USB_DP", "16": "ENDSTOP",
              "23": "TMC_UART", "24": "RX0",
              "25": "TX0", "28": "GND", "29": "GND"}
    sw4 = [("1", "A1", "passive"), ("2", "A2", "passive"),
           ("3", "B1", "passive"), ("4", "B2", "passive")]
    comps = [
        module_comp("ESP32-C6-WROOM-1", "U1", 100, 80, C6_WROOM_PINS, u1plan, B),
        {"sym": "USB_C_16P", "ref": "X1", "x": 30, "y": 55, "refp": "X",
         "pins": [(str(i), n, "passive") for i, n in enumerate(
             ["GND1", "VBUS1", "CC1", "DP1", "DM1", "SBU1", "VBUS2", "GND2",
              "GND3", "VBUS3", "SBU2", "DM2", "DP2", "CC2", "VBUS4", "GND4"],
             1)] + [("S1", "SH1", "passive"), ("S2", "SH2", "passive"),
                    ("S3", "SH3", "passive"), ("S4", "SH4", "passive")],
         "plan": USB_X1_PLAN},
        {"sym": "AP2112K-3.3", "ref": "U2", "x": 60, "y": 85, "refp": "U",
         "pins": [("1", "VIN", "passive"), ("2", "GND", "passive"),
                  ("3", "EN", "passive"), ("4", "NC", "passive"),
                  ("5", "VOUT", "passive")],
         "plan": {"1": "+5V", "2": "GND", "3": "+5V", "4": None, "5": "+3V3"}},
        {"sym": "AP63205", "ref": "U3", "x": 60, "y": 110, "refp": "U",
         "pins": [("1", "FB", "passive"), ("2", "GND", "passive"),
                  ("3", "VIN", "passive"), ("4", "SW", "passive"),
                  ("5", "EN", "passive"), ("6", "BST", "passive")],
         "plan": {"1": "FB", "2": "GND", "3": "VMOT", "4": "SW", "5": "+5V",
                  "6": "BST"}},
        {"sym": "Conn_01x08", "ref": "J3", "x": 170, "y": 55, "refp": "J",
         "pins": [("1", "EN", "passive"), ("2", "MS1", "passive"),
                  ("3", "MS2", "passive"), ("4", "DIAG", "passive"),
                  ("5", "INDEX", "passive"), ("6", "PDN_UART", "passive"),
                  ("7", "STEP", "passive"), ("8", "DIR", "passive")],
         "plan": {"1": "TMC_EN", "2": "+3V3", "3": "+3V3", "4": "DIAG",
                  "5": None, "6": "TMC_UART", "7": "STEP", "8": "DIR"}},
        {"sym": "Conn_01x08", "ref": "J4", "x": 170, "y": 85, "refp": "J",
         "pins": [("1", "VMOT", "passive"), ("2", "GND", "passive"),
                  ("3", "B2", "passive"), ("4", "B1", "passive"),
                  ("5", "A1", "passive"), ("6", "A2", "passive"),
                  ("7", "VDD", "passive"), ("8", "GND", "passive")],
         "plan": {"1": "VMOT", "2": "GND", "3": "MOT_B2", "4": "MOT_B1",
                  "5": "MOT_A1", "6": "MOT_A2", "7": "+3V3", "8": "GND"}},
        {"sym": "ScrewTerm_2P", "ref": "J7", "x": 170, "y": 115, "refp": "J",
         "pins": std2("VMOT"), "plan": {"1": "VMOT_IN", "2": "GND"}},
        {"sym": "ScrewTerm_2P", "ref": "J5", "x": 170, "y": 135, "refp": "J",
         "pins": std2("A"), "plan": {"1": "MOT_A1", "2": "MOT_A2"}},
        {"sym": "ScrewTerm_2P", "ref": "J6", "x": 170, "y": 155, "refp": "J",
         "pins": std2("B"), "plan": {"1": "MOT_B1", "2": "MOT_B2"}},
        {"sym": "Conn_01x03", "ref": "J8", "x": 170, "y": 175, "refp": "J",
         "pins": [("1", "3V3", "passive"), ("2", "SIG", "passive"),
                  ("3", "GND", "passive")],
         "plan": {"1": "+3V3", "2": "ENDSTOP", "3": "GND"}},
        {"sym": "SS34", "ref": "D3", "x": 210, "y": 70, "refp": "D",
         "pins": [("1", "K", "passive"), ("2", "A", "passive")],
         "plan": {"1": "VMOT", "2": "VMOT_IN"}},
        {"sym": "SS34", "ref": "D2", "x": 210, "y": 90, "refp": "D",
         "pins": [("1", "K", "passive"), ("2", "A", "passive")],
         "plan": {"1": "VBUS", "2": "+5V"}},
        {"sym": "100uF_35V", "ref": "C8", "x": 210, "y": 110, "refp": "C",
         "pins": std2("100uF"), "plan": {"1": "VMOT", "2": "GND"}},
        {"sym": "4.7uH", "ref": "L1", "x": 210, "y": 130, "refp": "L",
         "pins": std2("L"), "plan": {"1": "SW", "2": "+5V"}},
        {"sym": "22uF", "ref": "C6", "x": 210, "y": 150, "refp": "C",
         "pins": std2("22uF"), "plan": {"1": "+5V", "2": "GND"}},
        {"sym": "100nF", "ref": "C7", "x": 210, "y": 170, "refp": "C",
         "pins": std2("100nF"), "plan": {"1": "BST", "2": "SW"}},
        {"sym": "100k", "ref": "R10", "x": 230, "y": 70, "refp": "R",
         "pins": std2("100k"), "plan": {"1": "+5V", "2": "FB"}},
        {"sym": "100k", "ref": "R11", "x": 230, "y": 90, "refp": "R",
         "pins": std2("100k"), "plan": {"1": "FB", "2": "GND"}},
        {"sym": "SW_PUSH", "ref": "BT1", "x": 100, "y": 130, "refp": "BT",
         "pins": sw4, "plan": {"1": "EN", "2": "GND", "3": "EN", "4": "GND"}},
        {"sym": "SW_PUSH", "ref": "BT2", "x": 130, "y": 130, "refp": "BT",
         "pins": sw4, "plan": {"1": "BOOT", "2": "GND", "3": "BOOT",
                               "4": "GND"}},
        {"sym": "LED_RED", "ref": "D1", "x": 100, "y": 155, "refp": "D",
         "pins": [("1", "A", "passive"), ("2", "K", "passive")],
         "plan": {"1": "LED1_A", "2": "STAT_LED"}},
        {"sym": "1k", "ref": "R8", "x": 100, "y": 175, "refp": "R",
         "pins": std2("1k"), "plan": {"1": "+3V3", "2": "LED1_A"}},
        {"sym": "5.1k", "ref": "R3", "x": 60, "y": 140, "refp": "R",
         "pins": std2("5.1k"), "plan": {"1": "USB_CC1", "2": "GND"}},
        {"sym": "5.1k", "ref": "R4", "x": 80, "y": 140, "refp": "R",
         "pins": std2("5.1k"), "plan": {"1": "USB_CC2", "2": "GND"}},
        {"sym": "10k", "ref": "R7", "x": 130, "y": 155, "refp": "R",
         "pins": std2("10k"), "plan": {"1": "+3V3", "2": "EN"}},
        {"sym": "10uF", "ref": "C1", "x": 60, "y": 170, "refp": "C",
         "pins": std2("10uF"), "plan": {"1": "VBUS", "2": "GND"}},
        {"sym": "10uF", "ref": "C2", "x": 80, "y": 170, "refp": "C",
         "pins": std2("10uF"), "plan": {"1": "+3V3", "2": "GND"}},
        {"sym": "100nF", "ref": "C3", "x": 100, "y": 170, "refp": "C",
         "pins": std2("100nF"), "plan": {"1": "+3V3", "2": "GND"}},
    ]
    lib, sch = build_schematic(B, comps, powers=("GND", "+3V3", "VBUS",
                                                 "+5V", "VMOT"))
    lib.save(os.path.join(out, B + "-lib.kicad_sym"))
    sch.save(os.path.join(out, B + ".kicad_sch"))

    # ---------------- PCB (70 x 50) ----------------
    b = Board(B, 70.0, 50.0)
    b.keepout(8.8, 0.2, 27.2, 4.2, "ANTENNA KEEP-OUT")
    RC = (-1.05, -0.65, 1.05, 0.65)
    b.place(fps["ESP32-C6-WROOM-1"], "U1", "ESP32-C6-WROOM-1", 18, 16)
    place_usbc(b, 14.0, 50.0)
    b.place("Package_TO_SOT_SMD:SOT-23-5", "U2", "AP2112K-3.3", 26, 40,
            crtyd=(-1.6, -1.75, 1.6, 1.75))
    b.place("Package_TO_SOT_SMD:SOT-23-6", "U3", "AP63205", 38, 40,
            crtyd=(-1.7, -1.75, 1.7, 1.75))
    b.place("Diode_SMD:D_SMA", "D3", "SS34", 58, 44, crtyd=(-2.6, -1.6, 2.6, 1.6))
    b.place("Diode_SMD:D_SMA", "D2", "SS34", 20, 40, crtyd=(-2.6, -1.6, 2.6, 1.6))
    b.place("Capacitor_SMD:CP_Electrolytic_5x5.3", "C8", "100uF_35V", 50, 44,
            crtyd=(-3.0, -3.0, 3.0, 3.0))
    b.place(fps["IND-4040"], "L1", "4.7uH", 44, 41, crtyd=(-2.3, -2.3, 2.3, 2.3))
    b.place("Capacitor_SMD:C_0805_2012Metric", "C6", "22uF", 49, 38, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C7", "100nF", 34, 44, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R10", "100k", 34, 35.5, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R11", "100k", 34, 46.5, crtyd=RC)
    HH = "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical"
    b.place(HH, "J3", "Conn_01x08", 48, 8)
    b.place(HH, "J4", "Conn_01x08", 63.24, 8)
    b.place(fps["ScrewTerm-5.08-2P"], "J7", "ScrewTerm_2P", 60, 44)
    b.place(fps["ScrewTerm-5.08-2P"], "J5", "ScrewTerm_2P", 57, 30)
    b.place(fps["ScrewTerm-5.08-2P"], "J6", "ScrewTerm_2P", 57, 36)
    b.place("Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
            "J8", "Conn_01x03", 38, 4, rot=90)
    b.place(fps["Tactile-6x6-SMD"], "BT1", "SW_PUSH", 36, 12,
            crtyd=(-5.95, -3.15, 5.95, 3.15))
    b.place(fps["Tactile-6x6-SMD"], "BT2", "SW_PUSH", 36, 22,
            crtyd=(-5.95, -3.15, 5.95, 3.15))
    b.place("LED_SMD:LED_0603_1608Metric", "D1", "LED_RED", 42, 8,
            crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R8", "1k", 39, 8, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R3", "5.1k", 6, 40.5, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R4", "5.1k", 6, 43.0, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R7", "10k", 12.2, 12, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C1", "10uF", 8, 36.5,
            rot=180, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C2", "10uF", 22, 36.5,
            rot=180, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C3", "100nF", 8, 6, crtyd=RC)

    plans = {c["ref"]: c["plan"] for c in comps}
    b.assign(plans)

    # ---- VBUS: USB zones -> combine -> D2 -> C1 ----
    b.via("VBUS", 13.1, 45.5)
    b.via("VBUS", 17.1, 45.8)
    b.route("VBUS", [(13.1, 45.5), (17.1, 45.5), (17.1, 45.8)], layer="B.Cu",
            width=0.5)
    b.route("VBUS", [(17.1, 45.8), (17.1, 47.8), (19.5, 47.8)], layer="B.Cu",
            width=0.5)
    b.via("VBUS", 19.5, 47.8)
    b.route("VBUS", [(19.5, 47.8), (19.5, 40.0), b.P("D2", "1")])
    b.route("VBUS", [(17.1, 47.8), (8.5, 47.8)], layer="B.Cu", width=0.5)
    b.via("VBUS", 8.5, 47.8)
    b.route("VBUS", [(8.5, 47.8), (8.5, 36.5), b.P("C1", "1")])
    # ---- +5V: D2 p2 / L1 p2 / C6 / U2 VIN+EN / U3 EN ----
    _dx2 = b.P("D2", "2")
    b.route("+5V", [_dx2, (_dx2[0], 37.5), (24.5, 37.5)])
    b.route("+5V", [b.P("L1", "2"), (45.7, 41.0), (45.7, 37.5), (48.05, 37.5)])
    b.route("+5V", [(48.05, 37.5), b.P("C6", "1")])
    b.route("+5V", [(24.5, 37.5), (24.5, 39.05), (25.05, 39.05)])  # U2 VIN
    b.route("+5V", [(24.5, 37.5), (23.5, 37.5), (23.5, 40.95),
                    (25.05, 40.95)])                                # U2 EN
    b.route("+5V", [(38.95, 40.0), (40.5, 40.0), (40.5, 37.5),
                    (45.7, 37.5)])                                  # U3 EN p5
    # SW: U3 p4 -> L1 p1
    b.route("SW", [(38.95, 40.95), (40.5, 40.95), (40.5, 41.0), b.P("L1", "1")],
            width=0.5)
    # ---- VMOT: J7 p1 -> D3 -> C8 + U3 VIN + J4 p1 ----
    b.route("VMOT_IN", [b.P("J7", "1"), b.P("D3", "2")], width=0.8)
    _dx3 = b.P("D3", "1")
    b.route("VMOT", [_dx3, (55.95, 46.3), (48.55, 46.3), (48.55, 44.0)],
            width=0.8)
    b.route("VMOT", [(48.55, 44.0), (45.0, 44.0), (45.0, 45.5), (36.0, 45.5),
                     (36.0, 40.95), (37.05, 40.95)], width=0.8)
    b.route("VMOT", [(48.55, 46.3), (48.55, 48.9), (69.0, 48.9), (69.0, 8.0),
                     b.P("J4", "1")], width=0.8)
    # ---- +3V3: U2 VOUT -> trunk y=33 -> module, J4 VDD, J3 MS1/MS2, misc ----
    b.route("+3V3", [(26.95, 39.525), (28.5, 39.525), (28.5, 33.0),
                     (7.5, 33.0)])
    b.route("+3V3", [b.P("U1", "2"), (7.5, 9.01)])
    b.via("+3V3", 7.5, 9.01)
    b.route("+3V3", [(7.5, 9.01), (7.5, 33.0)], layer="B.Cu", width=0.5)
    b.via("+3V3", 7.5, 33.0)
    b.route("+3V3", [(7.225, 6.0), (7.225, 9.01), (7.5, 9.01)])     # C3 p1
    b.route("+3V3", [(28.5, 33.0), (65.0, 33.0)])                   # trunk right
    b.route("+3V3", [b.P("J4", "7"), (65.0, 23.24), (65.0, 33.0)])
    b.route("+3V3", [b.P("J3", "2"), (49.5, 10.54), (49.5, 30.0), (51.5, 30.0),
                     (51.5, 33.0)])                                  # MS1
    b.route("+3V3", [b.P("J3", "3"), (50.6, 13.08), (50.6, 29.0),
                     (51.5, 29.0)])                                  # MS2
    b.route("+3V3", [b.P("J8", "1"), (44.5, 4.0), (44.5, 6.5)])
    b.route("+3V3", [b.P("R8", "1"), (38.225, 6.5), (44.5, 6.5), (44.5, 33.0)])
    b.route("+3V3", [b.P("R7", "1"), (11.425, 12.0), (11.425, 33.0)])
    b.route("+3V3", [b.P("C2", "1"), (22.775, 36.5), (22.775, 33.0)])
    # LED link
    b.route("LED1_A", [b.P("R8", "2"), b.P("D1", "1")], width=0.25)

    b.gnd_stitch()
    finish_pcb(b, out, extra_silk=[
        ("BlindDriver-C6", 35, 2.5), ("EN", 36, 8.2), ("BOOT", 36, 18.2),
        ("TMC2209", 55.6, 5.0), ("VMOT 12-24V", 60, 40.2),
        ("MOTOR A", 57, 26.2), ("MOTOR B", 57, 33.0), ("ENDSTOP", 38, 6.5)])
    write_bom(B, out, [
        ("U1", "ESP32-C6-WROOM-1", 1), ("X1", "USB_C_16P", 1),
        ("U2", "AP2112K-3.3", 1), ("U3", "AP63205", 1),
        ("U4", "TMC2209", 1), ("J3,J4", "Conn_01x08", 2),
        ("J5,J6,J7", "ScrewTerm_2P", 3), ("J8", "Conn_01x03", 1),
        ("D2,D3", "SS34", 2), ("C8", "100uF_35V", 1), ("L1", "4.7uH", 1),
        ("C6", "22uF", 1), ("C7,C3", "100nF", 2), ("R10,R11", "100k", 2),
        ("BT1,BT2", "SW_PUSH", 2), ("D1", "LED_RED", 1), ("R8", "1k", 1),
        ("R3,R4", "5.1k", 2), ("R7", "10k", 1), ("C1,C2", "10uF", 2)])
    problems = kg.validate_project(out)
    if problems:
        for p in problems:
            print("VALIDATE:", p)
        raise SystemExit(f"{B}: validate_project failed")
    print(f"{B}: OK")



# ---------------------------------------------------------------------------
# Board: irblaster-c3 (40 x 30) -- IR climate bridge
# ---------------------------------------------------------------------------
def build_irblaster_c3():
    B = "irblaster-c3"
    out = os.path.join(BOARDS_ROOT, B)
    os.makedirs(out, exist_ok=True)
    fps = make_footprints(B)
    kg.write_project(os.path.join(out, B + ".kicad_pro"), B, B + "-lib")

    u1plan = {"1": "+3V3", "2": "EN", "3": "IR_TX", "4": "IR_RX", "5": "SDA",
              "6": "SCL", "7": None, "8": "BOOT", "9": "GND", "10": "STAT_LED",
              "11": "RX0", "12": "TX0", "13": "USB_DM", "14": "USB_DP",
              "19": "GND"}
    sw4 = [("1", "A1", "passive"), ("2", "A2", "passive"),
           ("3", "B1", "passive"), ("4", "B2", "passive")]
    comps = [
        module_comp("ESP32-C3-WROOM-02", "U1", 100, 80, C3_WROOM_PINS, u1plan, B),
        {"sym": "USB_C_16P", "ref": "X1", "x": 30, "y": 55, "refp": "X",
         "pins": [(str(i), n, "passive") for i, n in enumerate(
             ["GND1", "VBUS1", "CC1", "DP1", "DM1", "SBU1", "VBUS2", "GND2",
              "GND3", "VBUS3", "SBU2", "DM2", "DP2", "CC2", "VBUS4", "GND4"],
             1)] + [("S1", "SH1", "passive"), ("S2", "SH2", "passive"),
                    ("S3", "SH3", "passive"), ("S4", "SH4", "passive")],
         "plan": USB_X1_PLAN},
        {"sym": "AP2112K-3.3", "ref": "U2", "x": 60, "y": 85, "refp": "U",
         "pins": [("1", "VIN", "passive"), ("2", "GND", "passive"),
                  ("3", "EN", "passive"), ("4", "NC", "passive"),
                  ("5", "VOUT", "passive")], "plan": LDO_PLAN},
        {"sym": "TSOP38238", "ref": "U3", "x": 130, "y": 55, "refp": "U",
         "pins": [("1", "OUT", "passive"), ("2", "GND", "passive"),
                  ("3", "VS", "passive")],
         "plan": {"1": "IR_RX", "2": "GND", "3": "+3V3"}},
        {"sym": "BH1750", "ref": "U4", "x": 130, "y": 85, "refp": "U",
         "pins": [("1", "VCC", "passive"), ("2", "GND", "passive"),
                  ("3", "SCL", "passive"), ("4", "SDA", "passive"),
                  ("5", "ADDR", "passive"), ("6", "DVI", "passive"),
                  ("7", "EP", "passive")],
         "plan": {"1": "+3V3", "2": "GND", "3": "SCL", "4": "SDA",
                  "5": "GND", "6": "+3V3", "7": "GND"}},
        {"sym": "TSAL6200", "ref": "D2", "x": 165, "y": 50, "refp": "D",
         "pins": [("1", "A", "passive"), ("2", "K", "passive")],
         "plan": {"1": "VBUS", "2": "IR1_K"}},
        {"sym": "TSAL6200", "ref": "D3", "x": 165, "y": 75, "refp": "D",
         "pins": [("1", "A", "passive"), ("2", "K", "passive")],
         "plan": {"1": "VBUS", "2": "IR2_K"}},
        {"sym": "S8050", "ref": "Q1", "x": 165, "y": 100, "refp": "Q",
         "pins": [("1", "B", "passive"), ("2", "E", "passive"),
                  ("3", "C", "passive")],
         "plan": {"1": "IR_DRV", "2": "GND", "3": "IR_C"}},
        {"sym": "47R", "ref": "R6", "x": 190, "y": 50, "refp": "R",
         "pins": std2("47R"), "plan": {"1": "IR1_K", "2": "IR_C"}},
        {"sym": "47R", "ref": "R7", "x": 190, "y": 75, "refp": "R",
         "pins": std2("47R"), "plan": {"1": "IR2_K", "2": "IR_C"}},
        {"sym": "100R", "ref": "R9", "x": 190, "y": 100, "refp": "R",
         "pins": std2("100R"), "plan": {"1": "IR_TX", "2": "IR_DRV"}},
        {"sym": "4.7k", "ref": "R5", "x": 190, "y": 125, "refp": "R",
         "pins": std2("4.7k"), "plan": {"1": "+3V3", "2": "IR_RX"}},
        {"sym": "SW_PUSH", "ref": "BT1", "x": 60, "y": 115, "refp": "BT",
         "pins": sw4, "plan": {"1": "EN", "2": "GND", "3": "EN", "4": "GND"}},
        {"sym": "SW_PUSH", "ref": "BT2", "x": 90, "y": 115, "refp": "BT",
         "pins": sw4, "plan": {"1": "BOOT", "2": "GND", "3": "BOOT",
                               "4": "GND"}},
        {"sym": "LED_GRN", "ref": "D1", "x": 115, "y": 115, "refp": "D",
         "pins": [("1", "A", "passive"), ("2", "K", "passive")],
         "plan": {"1": "LED1_A", "2": "STAT_LED"}},
        {"sym": "1k", "ref": "R8", "x": 115, "y": 140, "refp": "R",
         "pins": std2("1k"), "plan": {"1": "+3V3", "2": "LED1_A"}},
        {"sym": "5.1k", "ref": "R3", "x": 30, "y": 90, "refp": "R",
         "pins": std2("5.1k"), "plan": {"1": "USB_CC1", "2": "GND"}},
        {"sym": "5.1k", "ref": "R4", "x": 45, "y": 90, "refp": "R",
         "pins": std2("5.1k"), "plan": {"1": "USB_CC2", "2": "GND"}},
        {"sym": "10k", "ref": "R2", "x": 90, "y": 140, "refp": "R",
         "pins": std2("10k"), "plan": {"1": "+3V3", "2": "EN"}},
        {"sym": "10uF", "ref": "C1", "x": 30, "y": 140, "refp": "C",
         "pins": std2("10uF"), "plan": {"1": "VBUS", "2": "GND"}},
        {"sym": "10uF", "ref": "C2", "x": 45, "y": 140, "refp": "C",
         "pins": std2("10uF"), "plan": {"1": "+3V3", "2": "GND"}},
        {"sym": "100nF", "ref": "C3", "x": 60, "y": 140, "refp": "C",
         "pins": std2("100nF"), "plan": {"1": "+3V3", "2": "GND"}},
        {"sym": "100nF", "ref": "C4", "x": 75, "y": 140, "refp": "C",
         "pins": std2("100nF"), "plan": {"1": "+3V3", "2": "GND"}},
        {"sym": "Conn_01x04", "ref": "J1", "x": 145, "y": 140, "refp": "J",
         "pins": [("1", "3V3", "passive"), ("2", "TX0", "passive"),
                  ("3", "RX0", "passive"), ("4", "GND", "passive")],
         "plan": {"1": "+3V3", "2": "TX0", "3": "RX0", "4": "GND"}},
    ]
    lib, sch = build_schematic(B, comps, powers=("GND", "+3V3", "VBUS"))
    lib.save(os.path.join(out, B + "-lib.kicad_sym"))
    sch.save(os.path.join(out, B + ".kicad_sch"))

    # ---------------- PCB (40 x 30) ----------------
    b = Board(B, 40.0, 30.0, mounting=[(3.5, 3.5), (36.5, 3.5), (7.5, 26.5)])
    b.keepout(3.55, 0.2, 22.45, 4.3, "ANTENNA KEEP-OUT")
    RC = (-1.05, -0.65, 1.05, 0.65)
    b.place(fps["ESP32-C3-WROOM-02"], "U1", "ESP32-C3-WROOM-02", 13, 12)
    place_usbc(b, 33.0, 30.0)
    b.place("Package_TO_SOT_SMD:SOT-23-5", "U2", "AP2112K-3.3", 25, 21.3,
            crtyd=(-1.6, -1.75, 1.6, 1.75))
    b.place(fps["TSOP38238"], "U3", "TSOP38238", 28, 8,
            crtyd=(-1.8, -4.3, 6.9, 1.1))
    b.place(fps["BH1750-WSOF6"], "U4", "BH1750", 28, 13,
            crtyd=(-1.85, -1.05, 1.85, 1.05))
    b.place(fps["IR-LED-5mm"], "D2", "TSAL6200", 35, 13)
    b.place(fps["IR-LED-5mm"], "D3", "TSAL6200", 35, 16.5)
    b.place("Package_TO_SOT_SMD:SOT-23", "Q1", "S8050", 31, 21.0,
            crtyd=(-1.5, -1.6, 1.5, 1.6))
    b.place("Resistor_SMD:R_0603_1608Metric", "R6", "47R", 35.5, 10.5, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R7", "47R", 35.5, 18.5, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R9", "100R", 25.5, 23.6, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R5", "4.7k", 24, 10, crtyd=RC)
    b.place(fps["Tactile-6x6-SMD"], "BT1", "SW_PUSH", 8, 24,
            crtyd=(-5.95, -3.15, 5.95, 3.15))
    b.place(fps["Tactile-6x6-SMD"], "BT2", "SW_PUSH", 23.5, 24,
            crtyd=(-5.95, -3.15, 5.95, 3.15))
    b.place("LED_SMD:LED_0603_1608Metric", "D1", "LED_GRN", 24, 6, rot=180, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R8", "1k", 26.5, 6, rot=180, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R3", "5.1k", 17, 23.5, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R4", "5.1k", 22, 25.6, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R2", "10k", 8, 8, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C1", "10uF", 36.5, 20.5,
            rot=180, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C2", "10uF", 21.4, 20.35,
            rot=180, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C3", "100nF", 7, 6, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C4", "100nF", 28, 16, crtyd=RC)
    b.place("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
            "J1", "Conn_01x04", 14.8, 28.0, rot=270)

    plans = {c["ref"]: c["plan"] for c in comps}
    b.assign(plans)

    # ---- VBUS: USB zones -> combine -> LDO, C1, IR LED anodes ----
    b.via("VBUS", 32.1, 25.5)
    b.via("VBUS", 36.1, 25.8)
    b.route("VBUS", [(32.1, 25.5), (36.1, 25.5), (36.1, 25.8)], layer="B.Cu",
            width=0.5)
    b.route("VBUS", [(36.1, 25.8), (36.1, 22.5), (34.775, 22.5)],
            layer="B.Cu", width=0.5)
    b.via("VBUS", 34.775, 22.5)
    b.route("VBUS", [(34.775, 22.5), (34.775, 20.5)])               # C1 p1
    b.route("VBUS", [(36.1, 22.5), (23.0, 22.5)], layer="B.Cu", width=0.5)
    b.via("VBUS", 23.0, 22.5)
    b.route("VBUS", [(23.0, 22.5), (23.0, 20.35), (24.05, 20.35)])  # U2 VIN
    b.route("VBUS", [(23.0, 22.5), (23.0, 22.25), (24.05, 22.25)])  # U2 EN
    b.route("VBUS", [(37.275, 22.5), (34.4, 22.5), (34.4, 13.0)], layer="B.Cu",
            width=0.5)
    b.via("VBUS", 34.4, 13.0)
    b.route("VBUS", [(34.4, 13.0), (35.0, 13.0)])                   # D2 anode
    b.via("VBUS", 34.4, 16.5)
    b.route("VBUS", [(34.4, 16.5), (35.0, 16.5)])                   # D3 anode
    # ---- +3V3 trunk y=20.0 ----
    b.route("+3V3", [(25.95, 20.825), (26.3, 20.825), (26.3, 19.4)])
    b.route("+3V3", [(4.5, 19.4), (33.5, 19.4)])
    b.route("+3V3", [b.P("U1", "1"), (2.8, 6.1)])
    b.via("+3V3", 2.8, 6.1)
    b.route("+3V3", [(2.8, 6.1), (2.8, 19.4)], layer="B.Cu", width=0.5)
    b.via("+3V3", 2.8, 19.4)
    b.route("+3V3", [(2.8, 19.4), (4.5, 19.4)])
    b.route("+3V3", [(6.225, 6.0), (6.225, 6.1), (4.25, 6.1)])      # C3 p1
    b.route("+3V3", [(22.175, 20.35), (22.175, 19.4)])              # C2 p1
    _p1 = b.P("U4", "1"); _p6 = b.P("U4", "6")
    b.route("+3V3", [_p1, (25.5, _p1[1]), (25.5, 19.4)])
    b.route("+3V3", [_p6, (30.8, _p6[1]), (30.8, 19.4)])
    b.route("+3V3", [(27.225, 16.0), (27.225, 19.4)])               # C4 p1
    b.route("+3V3", [(33.08, 8.0), (33.08, 19.4)])                  # U3 VS p3
    b.route("+3V3", [(23.225, 10.0), (23.225, 19.4)])               # R5 p1
    b.route("+3V3", [(27.275, 6.0), (31.8, 6.0), (31.8, 19.4)])   # R8 p1
    b.route("+3V3", [(7.225, 8.0), (6.5, 8.0), (6.5, 6.1)])         # R2 p1
    b.route("+3V3", [(14.8, 28.0), (14.8, 29.2), (10.0, 29.2),
                     (10.0, 19.4)])
    # LED link R8 p2 -> D1 p1
    b.route("LED1_A", [(25.725, 6.0), (24.775, 6.0)], width=0.25)

    b.gnd_stitch()
    finish_pcb(b, out, extra_silk=[
        ("IRBlaster-C3", 30, 2.5), ("EN", 8, 20.2), ("BOOT", 22, 20.2),
        ("IR TX", 33, 8.6), ("IR RX", 31.5, 4.2),
        ("3V3 TX RX GND", 14, 25.6)])
    write_bom(B, out, [
        ("U1", "ESP32-C3-WROOM-02", 1), ("X1", "USB_C_16P", 1),
        ("U2", "AP2112K-3.3", 1), ("U3", "TSOP38238", 1),
        ("U4", "BH1750", 1), ("D2,D3", "TSAL6200", 2), ("Q1", "S8050", 1),
        ("R6,R7", "47R", 2), ("R9", "100R", 1), ("R5", "4.7k", 1),
        ("R8", "1k", 1), ("R3,R4", "5.1k", 2), ("R2", "10k", 1),
        ("C1,C2", "10uF", 2), ("C3,C4", "100nF", 2), ("D1", "LED_GRN", 1),
        ("BT1,BT2", "SW_PUSH", 2), ("J1", "Conn_01x04", 1)])
    problems = kg.validate_project(out)
    if problems:
        for p in problems:
            print("VALIDATE:", p)
        raise SystemExit(f"{B}: validate_project failed")
    print(f"{B}: OK")

# ---------------------------------------------------------------------------
# Board: gardenprobe-c6 (70 x 25) -- battery soil-moisture stick node
# ---------------------------------------------------------------------------
def build_gardenprobe_c6():
    B = "gardenprobe-c6"
    out = os.path.join(BOARDS_ROOT, B)
    os.makedirs(out, exist_ok=True)
    fps = make_footprints(B)
    kg.write_project(os.path.join(out, B + ".kicad_pro"), B, B + "-lib")

    u1plan = {"1": "GND", "2": "+3V3", "3": "EN", "8": "SOIL_ADC",
              "9": "SOIL_CHG", "18": "I2C_SDA", "19": "I2C_SCL", "24": "RX0",
              "25": "TX0", "26": "LOAD_EN", "27": "BATT_ADC", "28": "GND",
              "29": "GND"}
    comps = [
        module_comp("ESP32-C6-WROOM-1", "U1", 100, 80, C6_WROOM_PINS, u1plan, B),
        {"sym": "JST_PH_2", "ref": "BT1", "x": 35, "y": 55, "refp": "BT",
         "pins": [("1", "+", "passive"), ("2", "-", "passive")],
         "plan": {"1": "VBAT", "2": "GND"}},
        {"sym": "MCP1700-3302", "ref": "U2", "x": 65, "y": 55, "refp": "U",
         "pins": [("1", "GND", "passive"), ("2", "VIN", "passive"),
                  ("3", "VOUT", "passive")],
         "plan": {"1": "GND", "2": "VBAT", "3": "+3V3"}},
        {"sym": "AO3401A", "ref": "Q1", "x": 95, "y": 55, "refp": "Q",
         "pins": [("1", "G", "passive"), ("2", "S", "passive"),
                  ("3", "D", "passive")],
         "plan": {"1": "LOAD_EN", "2": "+3V3", "3": "+3V3_SW"}},
        {"sym": "SHT31", "ref": "U3", "x": 140, "y": 55, "refp": "U",
         "pins": [("1", "SCL", "passive"), ("2", "VDD", "passive"),
                  ("3", "GND", "passive"), ("4", "SDA", "passive"),
                  ("5", "ADDR", "passive"), ("6", "NC", "passive"),
                  ("7", "NC", "passive"), ("8", "GND", "passive"),
                  ("9", "EP", "passive")],
         "plan": {"1": "I2C_SCL", "2": "+3V3_SW", "3": "GND", "4": "I2C_SDA",
                  "5": "GND", "6": None, "7": None, "8": "GND", "9": "GND"}},
        {"sym": "SOIL_PROBE", "ref": "J2", "x": 180, "y": 55, "refp": "J",
         "pins": std2("PROBE"), "plan": {"1": "SOIL_ADC", "2": "GND"}},
        {"sym": "10k", "ref": "R1", "x": 210, "y": 40, "refp": "R",
         "pins": std2("10k"), "plan": {"1": "+3V3", "2": "EN"}},
        {"sym": "100k", "ref": "R3", "x": 210, "y": 60, "refp": "R",
         "pins": std2("100k"), "plan": {"1": "VBAT", "2": "BATT_ADC"}},
        {"sym": "100k", "ref": "R4", "x": 210, "y": 80, "refp": "R",
         "pins": std2("100k"), "plan": {"1": "BATT_ADC", "2": "GND"}},
        {"sym": "1M", "ref": "R5", "x": 210, "y": 100, "refp": "R",
         "pins": std2("1M"), "plan": {"1": "SOIL_CHG", "2": "SOIL_ADC"}},
        {"sym": "4.7k", "ref": "R6", "x": 210, "y": 120, "refp": "R",
         "pins": std2("4.7k"), "plan": {"1": "+3V3_SW", "2": "I2C_SCL"}},
        {"sym": "4.7k", "ref": "R7", "x": 210, "y": 140, "refp": "R",
         "pins": std2("4.7k"), "plan": {"1": "+3V3_SW", "2": "I2C_SDA"}},
        {"sym": "10uF", "ref": "C1", "x": 235, "y": 60, "refp": "C",
         "pins": std2("10uF"), "plan": {"1": "VBAT", "2": "GND"}},
        {"sym": "100nF", "ref": "C2", "x": 235, "y": 80, "refp": "C",
         "pins": std2("100nF"), "plan": {"1": "+3V3", "2": "GND"}},
        {"sym": "100nF", "ref": "C3", "x": 235, "y": 100, "refp": "C",
         "pins": std2("100nF"), "plan": {"1": "+3V3", "2": "GND"}},
        {"sym": "100nF", "ref": "C4", "x": 235, "y": 120, "refp": "C",
         "pins": std2("100nF"), "plan": {"1": "EN", "2": "GND"}},
        {"sym": "Conn_01x04", "ref": "J1", "x": 145, "y": 150, "refp": "J",
         "pins": [("1", "3V3", "passive"), ("2", "TX0", "passive"),
                  ("3", "RX0", "passive"), ("4", "GND", "passive")],
         "plan": {"1": "+3V3", "2": "TX0", "3": "RX0", "4": "GND"}},
    ]
    lib, sch = build_schematic(B, comps, powers=("GND", "+3V3"))
    lib.save(os.path.join(out, B + "-lib.kicad_sym"))
    sch.save(os.path.join(out, B + ".kicad_sch"))

    # ---------------- PCB (70 x 25) ----------------
    b = Board(B, 70.0, 25.0, mounting=[(45.0, 3.5), (45.0, 21.5)])
    b.keepout(0.2, 3.0, 4.5, 20.5, "ANTENNA KEEP-OUT")
    RC = (-1.05, -0.65, 1.05, 0.65)
    b.place(fps["ESP32-C6-WROOM-1"], "U1", "ESP32-C6-WROOM-1", 13.5, 12.5,
            rot=270)
    b.place(fps["JST-PH-2"], "BT1", "JST_PH_2", 36, 6)
    b.place("Package_TO_SOT_SMD:SOT-23", "U2", "MCP1700-3302", 35, 17,
            crtyd=(-1.5, -1.6, 1.5, 1.6))
    b.place("Package_TO_SOT_SMD:SOT-23", "Q1", "AO3401A", 41, 12,
            crtyd=(-1.5, -1.6, 1.5, 1.6))
    b.place(fps["SHT31-DFN8"], "U3", "SHT31", 48, 17,
            crtyd=(-1.75, -1.75, 1.75, 1.75))
    b.place(fps["SoilProbe-BCu"], "J2", "SOIL_PROBE", 61, 12.5)
    b.place("Resistor_SMD:R_0603_1608Metric", "R1", "10k", 3.5, 22.6, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R3", "100k", 44, 8, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R4", "100k", 43.5, 11, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R5", "1M", 43, 14, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R6", "4.7k", 47, 9, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R7", "4.7k", 50.5, 9, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C1", "10uF", 33.5, 12.5,
            crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C2", "100nF", 24.5, 16,
            crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C3", "100nF", 39.5, 21,
            crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C4", "100nF", 12, 22.6,
            crtyd=RC)
    b.place("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
            "J1", "Conn_01x04", 24, 21.5, rot=270)

    plans = {c["ref"]: c["plan"] for c in comps}
    b.assign(plans)

    # ---- VBAT: JST -> U2 VIN, C1 ----
    b.route("VBAT", [(36, 6), (36, 10), (33.0, 10), (33.0, 17.48),
                     (34.05, 17.48)])
    b.route("VBAT", [(32.725, 12.5), (33.0, 12.5)])                  # C1 p1
    # ---- +3V3: U2 VOUT -> trunk -> module / caps / Q1 / J1 / R1 ----
    b.route("+3V3", [(35.95, 17), (37.5, 17), (37.5, 21), (38.725, 21)])
    b.route("+3V3", [(37.5, 17), (37.5, 12.48), (40.05, 12.48)])   # Q1 S
    b.route("+3V3", [(23.725, 16), (23.725, 18.5), (37.5, 18.5), (37.5, 17)])
    b.route("+3V3", [(23.725, 16), (23.725, 23.9), (6.51, 23.9),
                     (6.51, 21.25)])                                 # U1 VDD
    b.route("+3V3", [(24, 21.5), (24, 23.9)])                        # J1 p1
    b.route("+3V3", [(2.725, 22.6), (2.725, 23.9), (6.51, 23.9)])    # R1 p1
    # ---- +3V3_SW: Q1 D -> SHT31 VDD + I2C pull-ups (switched rail) ----
    b.route("+3V3_SW", [(41.95, 12), (45.5, 12), (45.5, 16.6),
                        (46.8, 16.6)])
    b.route("+3V3_SW", [(45.5, 12), (45.5, 10.5)])
    b.route("+3V3_SW", [(46.225, 9), (46.225, 10.5), (45.5, 10.5)])
    b.route("+3V3_SW", [(49.725, 9), (49.725, 10.5), (45.5, 10.5)])

    b.gnd_stitch()
    finish_pcb(b, out, extra_silk=[
        ("GardenProbe-C6", 30, 2.5), ("BAT 3.7V", 38, 2.5),
        ("SOIL", 61, 23.5), ("3V3 TX RX GND", 24, 19.3)])
    write_bom(B, out, [
        ("U1", "ESP32-C6-WROOM-1", 1), ("BT1", "JST_PH_2", 1),
        ("U2", "MCP1700-3302", 1), ("Q1", "AO3401A", 1), ("U3", "SHT31", 1),
        ("J2", "SOIL_PROBE", 1), ("R1", "10k", 1), ("R3,R4", "100k", 2),
        ("R5", "1M", 1), ("R6,R7", "4.7k", 2), ("C1", "10uF", 1),
        ("C2,C3,C4", "100nF", 3), ("J1", "Conn_01x04", 1)])
    problems = kg.validate_project(out)
    if problems:
        for p in problems:
            print("VALIDATE:", p)
        raise SystemExit(f"{B}: validate_project failed")
    print(f"{B}: OK")


# ---------------------------------------------------------------------------
# Board: threadrcp-h2 (35 x 20) -- OpenThread RCP / Zigbee USB dongle
# ---------------------------------------------------------------------------
def build_threadrcp_h2():
    B = "threadrcp-h2"
    out = os.path.join(BOARDS_ROOT, B)
    os.makedirs(out, exist_ok=True)
    fps = make_footprints(B)
    kg.write_project(os.path.join(out, B + ".kicad_pro"), B, B + "-lib")

    u1plan = {"1": "GND", "2": "GND", "3": "+3V3", "8": "EN", "11": "GND",
              "14": "GND", "15": "+3V3", "22": "STAT_LED", "23": "BOOT",
              "26": "USB_DM", "27": "USB_DP", "30": "RX0", "31": "TX0",
              "36": "GND", "37": "GND", "38": "GND", "39": "GND", "40": "GND",
              "41": "GND", "42": "GND", "43": "GND", "44": "GND", "45": "GND",
              "46": "GND", "47": "GND", "48": "GND", "49": "GND", "50": "GND",
              "51": "GND", "52": "GND", "53": "GND"}
    x1plan = dict(USB_X1_PLAN)
    x1plan.update({"4": "USB_DP", "13": "USB_DP", "5": "USB_DM",
                   "12": "USB_DM"})
    comps = [
        module_comp("ESP32-H2-MINI-1", "U1", 100, 85, H2_MINI_PINS, u1plan, B),
        {"sym": "USB_C_16P", "ref": "X1", "x": 30, "y": 60, "refp": "X",
         "pins": [(str(i), n, "passive") for i, n in enumerate(
             ["GND1", "VBUS1", "CC1", "DP1", "DM1", "SBU1", "VBUS2", "GND2",
              "GND3", "VBUS3", "SBU2", "DM2", "DP2", "CC2", "VBUS4", "GND4"],
             1)] + [("S1", "SH1", "passive"), ("S2", "SH2", "passive"),
                    ("S3", "SH3", "passive"), ("S4", "SH4", "passive")],
         "plan": x1plan},
        {"sym": "AP2112K-3.3", "ref": "U2", "x": 60, "y": 90, "refp": "U",
         "pins": [("1", "VIN", "passive"), ("2", "GND", "passive"),
                  ("3", "EN", "passive"), ("4", "NC", "passive"),
                  ("5", "VOUT", "passive")], "plan": LDO_PLAN},
        {"sym": "SW_PUSH", "ref": "BT1", "x": 30, "y": 115, "refp": "BT",
         "pins": [("1", "A1", "passive"), ("2", "A2", "passive"),
                  ("3", "B1", "passive"), ("4", "B2", "passive")],
         "plan": {"1": "EN", "2": "GND", "3": "EN", "4": "GND"}},
        {"sym": "SW_PUSH", "ref": "BT2", "x": 60, "y": 115, "refp": "BT",
         "pins": [("1", "A1", "passive"), ("2", "A2", "passive"),
                  ("3", "B1", "passive"), ("4", "B2", "passive")],
         "plan": {"1": "BOOT", "2": "GND", "3": "BOOT", "4": "GND"}},
        {"sym": "LED_RED", "ref": "D1", "x": 175, "y": 60, "refp": "D",
         "pins": [("1", "A", "passive"), ("2", "K", "passive")],
         "plan": {"1": "LED1_A", "2": "GND"}},
        {"sym": "LED_GRN", "ref": "D2", "x": 175, "y": 90, "refp": "D",
         "pins": [("1", "A", "passive"), ("2", "K", "passive")],
         "plan": {"1": "LED2_A", "2": "STAT_LED"}},
        {"sym": "1k", "ref": "R8", "x": 175, "y": 40, "refp": "R",
         "pins": std2("1k"), "plan": {"1": "+3V3", "2": "LED1_A"}},
        {"sym": "1k", "ref": "R9", "x": 195, "y": 40, "refp": "R",
         "pins": std2("1k"), "plan": {"1": "+3V3", "2": "LED2_A"}},
        {"sym": "5.1k", "ref": "R3", "x": 90, "y": 115, "refp": "R",
         "pins": std2("5.1k"), "plan": {"1": "USB_CC1", "2": "GND"}},
        {"sym": "5.1k", "ref": "R4", "x": 110, "y": 115, "refp": "R",
         "pins": std2("5.1k"), "plan": {"1": "USB_CC2", "2": "GND"}},
        {"sym": "10k", "ref": "R7", "x": 175, "y": 115, "refp": "R",
         "pins": std2("10k"), "plan": {"1": "+3V3", "2": "EN"}},
        {"sym": "10uF", "ref": "C1", "x": 90, "y": 140, "refp": "C",
         "pins": std2("10uF"), "plan": {"1": "VBUS", "2": "GND"}},
        {"sym": "10uF", "ref": "C2", "x": 110, "y": 140, "refp": "C",
         "pins": std2("10uF"), "plan": {"1": "+3V3", "2": "GND"}},
        {"sym": "100nF", "ref": "C3", "x": 130, "y": 140, "refp": "C",
         "pins": std2("100nF"), "plan": {"1": "+3V3", "2": "GND"}},
        {"sym": "100nF", "ref": "C4", "x": 150, "y": 140, "refp": "C",
         "pins": std2("100nF"), "plan": {"1": "EN", "2": "GND"}},
    ]
    lib, sch = build_schematic(B, comps, powers=("GND", "+3V3", "VBUS"))
    lib.save(os.path.join(out, B + "-lib.kicad_sym"))
    sch.save(os.path.join(out, B + ".kicad_sch"))

    # ---------------- PCB (35 x 20) ----------------
    b = Board(B, 35.0, 20.0,
              mounting=[(2.2, 16.5), (31.5, 16.5), (25.5, 1.5)])
    b.keepout(0.2, 0.2, 1.6, 19.8, "ANTENNA KEEP-OUT")
    RC = (-1.05, -0.65, 1.05, 0.65)
    b.place(fps["ESP32-H2-MINI-1"], "U1", "ESP32-H2-MINI-1", 10, 6.8, rot=270)
    place_usbc(b, 17.0, 20.0)
    b.place("Package_TO_SOT_SMD:SOT-23-5", "U2", "AP2112K-3.3", 21, 8.5,
            crtyd=(-1.6, -1.75, 1.6, 1.75))
    b.place(fps["Tactile-6x6-SMD"], "BT1", "SW_PUSH", 26, 3.4,
            crtyd=(-5.95, -3.15, 5.95, 3.15))
    b.place(fps["Tactile-6x6-SMD"], "BT2", "SW_PUSH", 28.3, 16.8,
            crtyd=(-5.95, -3.15, 5.95, 3.15))
    b.place("LED_SMD:LED_0603_1608Metric", "D1", "LED_RED", 33.5, 4.5,
            rot=180, crtyd=RC)
    b.place("LED_SMD:LED_0603_1608Metric", "D2", "LED_GRN", 33.5, 11.5,
            crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R8", "1k", 33.5, 1.8, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R9", "1k", 28.5, 18.5, crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R3", "5.1k", 13.5, 17.9,
            crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R4", "5.1k", 18.3, 17.9,
            crtyd=RC)
    b.place("Resistor_SMD:R_0603_1608Metric", "R7", "10k", 6.0, 4.2, crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C1", "10uF", 24, 17.5,
            crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C2", "10uF", 25.5, 8.5,
            crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C3", "100nF", 15.5, 3.4,
            crtyd=RC)
    b.place("Capacitor_SMD:C_0603_1608Metric", "C4", "100nF", 12.5, 2.6,
            crtyd=RC)

    plans = {c["ref"]: c["plan"] for c in comps}
    b.assign(plans)

    # ---- VBUS: USB zones -> B.Cu trunk -> LDO VIN/EN + C1 ----
    b.via("VBUS", 15.3, 16.6)
    b.route("VBUS", [(15.3, 16.6), (15.3, 18.5), (27.5, 18.5), (27.5, 11.5)],
            layer="B.Cu", width=0.5)
    b.via("VBUS", 21.6, 18.8)
    b.route("VBUS", [(21.6, 18.8), (21.6, 18.5)], layer="B.Cu", width=0.5)
    b.route("VBUS", [(21.6, 18.8), (21.6, 17.6), (23.225, 17.6),
                     (23.225, 17.5)])                                 # C1 p1
    b.via("VBUS", 27.5, 11.5)
    b.route("VBUS", [(27.5, 11.5), (27.5, 6.9), (20.05, 6.9),
                     (20.05, 7.55)])                                  # U2 VIN
    b.route("VBUS", [(20.05, 9.45), (20.05, 10.2)])                 # U2 EN p3
    b.via("VBUS", 20.05, 10.2)
    b.route("VBUS", [(20.05, 10.2), (27.5, 10.2)], layer="B.Cu", width=0.5)
    # ---- +3V3: LDO VOUT -> B.Cu trunk -> module / caps ----
    b.route("+3V3", [(21.95, 8.02), (24.725, 8.02), (24.725, 8.5)])  # C2 p1
    b.route("+3V3", [(24.725, 8.5), (24.725, 12.9), (25.0, 12.9)])
    b.via("+3V3", 25.0, 12.9)
    b.route("+3V3", [(25.0, 12.9), (25.0, 17.7), (16.4, 17.7),
                     (16.4, 16.9)], layer="B.Cu", width=0.5)
    b.via("+3V3", 16.4, 16.9)
    b.route("+3V3", [(16.4, 16.9), (16.4, 19.0), (5.0, 19.0)])
    b.via("+3V3", 5.0, 19.0)
    b.route("+3V3", [(5.0, 19.0), (5.0, 14.8), (10.3, 14.8),
                     (10.3, 12.7)])                                  # U1 p3
    b.route("+3V3", [(17.6, 9.2), (19.0, 9.2), (19.0, 11.4)])       # U1 p15
    b.via("+3V3", 19.0, 11.4)
    b.route("+3V3", [(19.0, 11.4), (25.0, 11.4), (25.0, 12.9)],
            layer="B.Cu", width=0.5)
    b.route("+3V3", [(14.725, 3.4), (14.725, 2.0)])                 # C3 p1
    b.via("+3V3", 14.725, 2.0)
    b.route("+3V3", [(14.725, 2.0), (14.725, 12.5), (25.0, 12.5),
                     (25.0, 12.9)], layer="B.Cu", width=0.5)
    b.route("+3V3", [(5.225, 4.2), (5.225, 5.9)])                   # R7 p1
    b.via("+3V3", 5.225, 5.9)
    b.route("+3V3", [(5.225, 5.9), (14.725, 5.9)], layer="B.Cu", width=0.5)
    # LED link R8 p2 -> D1 p1
    b.route("LED1_A", [(34.275, 1.8), (34.275, 4.5)], width=0.25)

    b.gnd_stitch()
    finish_pcb(b, out, extra_silk=[
        ("ThreadRCP-H2", 26, 2.5), ("EN", 26, 1.9), ("BOOT", 27.5, 7.7),
        ("PWR", 31.5, 4.5), ("STAT", 31.5, 11.5)])
    write_bom(B, out, [
        ("U1", "ESP32-H2-MINI-1", 1), ("X1", "USB_C_16P", 1),
        ("U2", "AP2112K-3.3", 1), ("BT1,BT2", "SW_PUSH", 2),
        ("D1", "LED_RED", 1), ("D2", "LED_GRN", 1), ("R8,R9", "1k", 2),
        ("R3,R4", "5.1k", 2), ("R7", "10k", 1), ("C1,C2", "10uF", 2),
        ("C3,C4", "100nF", 2)])
    problems = kg.validate_project(out)
    if problems:
        for p in problems:
            print("VALIDATE:", p)
        raise SystemExit(f"{B}: validate_project failed")
    print(f"{B}: OK")


BUILDERS = {
    "threadnode-h2": build_threadnode_h2,
    "airquality-s3": build_airquality_s3,
    "blinddriver-c6": build_blinddriver_c6,
    "irblaster-c3": build_irblaster_c3,
    "gardenprobe-c6": build_gardenprobe_c6,
    "threadrcp-h2": build_threadrcp_h2,
}


def build(board):
    BUILDERS[board]()


if __name__ == "__main__":
    names = sys.argv[1:] or list(BUILDERS)
    for n in names:
        build(n)
