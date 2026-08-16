# <BOARD-NAME> — Component Datasheets
<!-- assembly: smd -->
<!-- board: <directory name under boards/> -->

| Designator(s) | Part Number | Manufacturer | Datasheet URL | Notes |
|---|---|---|---|---|
| U1 | ESP32-C3-MINI-1 | Espressif | https://www.espressif.com/sites/default/files/documentation/esp32-c3-mini-1_datasheet_en.pdf | MCU module |
| U2 | SHT31-DIS-B | Sensirion | https://sensirion.com/media/documents/213E6A3B/63A5A569/Datasheet_SHT3x_DIS.pdf | Temp/RH |
| U3 | PCF8574T | NXP | https://www.nxp.com/docs/en/data-sheet/PCF8574_PCF8574A.pdf | I2C GPIO expander |
| J1 | USB4085-GF-A | Global Connector Technology | https://gct.co/files/drawings/usb4085.pdf | USB-C connector |
| R1–R10, C1–C10 | 0603 generic | Yageo | https://www.yageo.com/upload/media/product/productsearch/datasheet/rchip/PYu-RC_Group_51_RoHS_L_12.pdf | Commodity passives, one row per series |

Guidelines:
- One row per unique part number, designators grouped.
- `TBD` in the URL column fails CI — find the sheet before merging.
- Modules (e.g. ESP32-C3-MINI) count as components: they need a row too.
