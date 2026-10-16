# Raspberry Pi Hardware Setup & Wiring Guide

This guide details the physical hardware wiring, pin assignments, electrical requirements, and schematic layout for connecting dual DS18B20 digital temperature probes, an Adafruit DHT22 humidity sensor, a 20x4 I2C character LCD, and an active-LOW relay module to a Raspberry Pi.

---

## 1. Raspberry Pi 40-Pin GPIO Header Reference

```
                             3.3V Power [01] [02] 5V Power
             (SDA1 / LCD) GPIO 2 / Pin 3 [03] [04] 5V Power (LCD / Relay VCC)
             (SCL1 / LCD) GPIO 3 / Pin 5 [05] [06] Ground (Common GND)
(DS18B20 1-Wire Data Bus) GPIO 4 / Pin 7 [07] [08] GPIO 14 (UART TX)
                                  Ground [09] [10] GPIO 15 (UART RX)
            (Relay Control) GPIO 17 / Pin 11 [11] [12] GPIO 18 (PCM CLK)
                            GPIO 27 / Pin 13 [13] [14] Ground
           (DHT22 Data Line) GPIO 22 / Pin 15 [15] [16] GPIO 23
                             3.3V Power [17] [18] GPIO 24
               (SPI0 MOSI) GPIO 10 / Pin 19 [19] [20] Ground
               (SPI0 MISO) GPIO 9  / Pin 21 [21] [22] GPIO 25
               (SPI0 SCLK) GPIO 11 / Pin 23 [23] [24] GPIO 8 (SPI0 CE0)
                                  Ground [25] [26] GPIO 7 (SPI0 CE1)
                            ID_SD (I2C) [27] [28] ID_SC (I2C)
                             GPIO 5 / Pin 29 [29] [30] Ground
                             GPIO 6 / Pin 31 [31] [32] GPIO 12 (PWM0)
                            GPIO 13 / Pin 33 [33] [34] Ground
                            GPIO 19 / Pin 35 [35] [36] GPIO 16
                            GPIO 26 / Pin 37 [37] [38] GPIO 20
                                  Ground [39] [40] GPIO 21
```

---

## 2. Bill of Materials (BOM)

| Component | Quantity | Key Specifications |
| :--- | :--- | :--- |
| **Raspberry Pi** | 1 | 3B+, 4B, or Zero 2 W running Raspberry Pi OS |
| **DS18B20 Probes** | 2 | Waterproof stainless steel casing, 1-Wire bus |
| **Pull-Up Resistor** | 1 | $4.7\,\text{k}\Omega$ (for DS18B20 1-Wire bus) |
| **DHT22 / AM2302** | 1 | Digital humidity sensor (internal or external $10\,\text{k}\Omega$ pull-up) |
| **20x4 Character LCD** | 1 | With soldered PCF8574 I2C backpack |
| **Relay Module** | 1 | 5V single-channel, opto-isolated, active-LOW |
| **Power Supply** | 1 | Official Raspberry Pi 5.1V / 3.0A USB-C (or micro-USB) power brick |
| **Prototyping / Wiring** | — | Breadboard/terminal block breakout, jumper wires |

---

## 3. Subsystem Wiring Breakdown

### A. Dual DS18B20 1-Wire Temperature Probes

The DS18B20 uses the Dallas 1-Wire protocol. Both probes connect in parallel to the exact same GPIO pin and are addressed individually by their unique factory-burned 64-bit ROM IDs.

* **Operating Voltage:** $3.3\,\text{V}$
* **Signal Pin:** Physical Pin 7 (`GPIO 4`)
* **Pull-up Requirement:** A single $4.7\,\text{k}\Omega$ resistor connected between the **Data Line** and **$3.3\,\text{V}$**.

```
            +3.3V (Pin 1) ------------------------+
                                                 |
                                               [4.7kΩ]
                                                 |
            GPIO 4 (Pin 7) -------+--------------+
                                  |              |
                                  |              |
             Probe 1 (Hot)        |              |
             +---------------+    |              |
             | Red   (VCC)   |----+              |
             | Yellow (DATA) |-------------------+
             | Black (GND)   |----+
             +---------------+    |
                                  |
             Probe 2 (Cool)       |
             +---------------+    |
             | Red   (VCC)   |----+
             | Yellow (DATA) |-------------------+
             | Black (GND)   |----+
             +---------------+    |
                                  |
            GND (Pin 9) ----------+
```

> **Note:** Wire color conventions can vary:
> * Standard: Red ($V_{\text{CC}}$), Yellow/White ($\text{Data}$), Black/Blue ($\text{GND}$).

---

### B. DHT22 Humidity Sensor

The DHT22 was assigned to **GPIO 22** to avoid data conflicts on the 1-Wire bus.

* **Operating Voltage:** $3.3\,\text{V}$ (recommended for direct $3.3\,\text{V}$ logic compatibility)
* **Signal Pin:** Physical Pin 15 (`GPIO 22`)

```
DHT22 Pin   Pin Name   Raspberry Pi Connection
---------   --------   -----------------------
Pin 1       VCC        Physical Pin 17 (3.3V)
Pin 2       DATA       Physical Pin 15 (GPIO 22)
Pin 3       NC         Not Connected
Pin 4       GND        Physical Pin 14 (Ground)
```

*(If using a bare 4-pin DHT22 without an integrated PCB breakout, connect a $10\,\text{k}\Omega$ resistor between Pin 1 ($V_{\text{CC}}$) and Pin 2 ($\text{DATA}$). Pre-mounted 3-pin breakout modules already feature this pull-up on board).*

---

### C. 20x4 I2C Character LCD (PCF8574 Backpack)

The LCD communicates over standard hardware I2C bus 1. The HD44780 controller and backlight run best at $5\,\text{V}$. The PCF8574 backpack typically handles the logic level interfacing safely via pull-ups to the Raspberry Pi's $3.3\,\text{V}$ bus lines.

```
LCD Backpack Pin   Raspberry Pi Connection
----------------   -----------------------
GND                Physical Pin 6 (Ground)
VCC                Physical Pin 2 (5V Power)
SDA                Physical Pin 3 (GPIO 2 / I2C1 SDA)
SCL                Physical Pin 5 (GPIO 3 / I2C1 SCL)
```

> **Contrast Adjustment:** If the display powers on with only solid rectangles or blank lines, turn the small blue potentiometer on the back of the PCF8574 backpack using a small screwdriver until characters become visible.

---

### D. Single-Channel Relay Module (Irrigation Control)

The relay controls high-voltage/external DC loads (e.g., $12\,\text{V}$ misting pumps, solenoid valves). It uses an **active-LOW** opto-coupler circuit driven via a safe high-impedance release pattern.

```
Relay Module Pin   Raspberry Pi Connection
----------------   -----------------------
VCC                Physical Pin 4 (5V Power)
GND                Physical Pin 20 (Ground)
IN                 Physical Pin 11 (GPIO 17)
```

#### High-Voltage / Load Side Wiring:
* **COM (Common):** Connect to the positive terminal of the external pump power supply.
* **NO (Normally Open):** Connect to the positive input of the pump or solenoid.
* **Negative Return:** Connect the negative return of the pump directly to the negative terminal of the external power supply.

*(Never route high-voltage external power into the Raspberry Pi rails. The relay's switch side is completely galvanically isolated).*

---

## 4. Master Pinout Connection Summary

| Physical Header Pin | BCM GPIO Number | Wire Destination | Subsystem Function |
| :--- | :--- | :--- | :--- |
| **Pin 1** | $3.3\,\text{V}$ | 1-Wire Resistor & DS18B20 Red wires | Sensor Power Rail ($3.3\,\text{V}$) |
| **Pin 2** | $5.0\,\text{V}$ | I2C LCD Backpack `VCC` | Display Power ($5\,\text{V}$) |
| **Pin 3** | `GPIO 2` | I2C LCD Backpack `SDA` | I2C Serial Data |
| **Pin 4** | $5.0\,\text{V}$ | Relay Module `VCC` | Relay Coil / Opto Power |
| **Pin 5** | `GPIO 3` | I2C LCD Backpack `SCL` | I2C Serial Clock |
| **Pin 6** | `GND` | I2C LCD Backpack `GND` | Common Ground |
| **Pin 7** | `GPIO 4` | DS18B20 Yellow wires (with $4.7\,\text{k}\Omega$ pull-up) | 1-Wire Temperature Bus |
| **Pin 9** | `GND` | DS18B20 Black wires | Common Ground |
| **Pin 11** | `GPIO 17` | Relay Module `IN` | Solenoid / Pump Trigger |
| **Pin 14** | `GND` | DHT22 `GND` | Common Ground |
| **Pin 15** | `GPIO 22` | DHT22 `DATA` | Humidity Sensor Bus |
| **Pin 17** | $3.3\,\text{V}$ | DHT22 `VCC` | Humidity Sensor Power ($3.3\,\text{V}$) |
| **Pin 20** | `GND` | Relay Module `GND` | Common Ground |

---

## 5. Verification Checklist

1. **Common Ground:** Verify that all sensors, the LCD backpack, and the relay module share a common ground reference with the Raspberry Pi ground pins.
2. **$4.7\,\text{k}\Omega$ Pull-Up:** Confirm the resistor is bridging the data line (`GPIO 4`) to **$3.3\,\text{V}$**, NOT $5\,\text{V}$. Connecting 1-Wire data lines directly to $5\,\text{V}$ can permanently damage the Pi's GPIO silicon.
3. **Relay Safety Inspection:** Ensure the relay control line is wired to `GPIO 17` (Physical Pin 11) and the load terminals on the relay board are secure and isolated inside an enclosure.