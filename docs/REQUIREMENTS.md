# Project Requirements & Bill of Materials (BOM)

This document details the complete hardware bill of materials, external power requirements, tooling consumables, and software dependencies for deploying the reptile enclosure environmental monitoring and irrigation system.

---

## 1. Hardware Bill of Materials (Core Components)

| Item | Component | Qty | Key Specifications / Notes | Example Part / Vendor |
| :--- | :--- | :--- | :--- | :--- |
| **H1** | Single-Board Computer | 1 | Raspberry Pi 3B+, 4B, or Zero 2 W (Raspberry Pi OS Bullseye/Bookworm) | Raspberry Pi 4 Model B (2GB/4GB) |
| **H2** | Dual Digital Temperature Probes | 2 | Waterproof DS18B20 stainless steel probe, 1-Wire interface, $-55^\circ\text{C}$ to $+125^\circ\text{C}$ range | Waterproof DS18B20 ($1\text{m}$ to $2\text{m}$ lead) |
| **H3** | Humidity & Temperature Sensor | 1 | DHT22 / AM2302 capacitive humidity ($0\text{–}100\%\,\text{RH}$, $\pm 2\text{–}5\%$) | Adafruit AM2302 / DHT22 sensor module |
| **H4** | Character Display | 1 | 20x4 Character LCD module with integrated PCF8574 $I^2C$ backpack (Address default `0x27` or `0x3F`) | HD44780 2004 LCD + $I^2C$ Backpack |
| **H5** | Relay Module | 1 | 1-Channel $5\text{V}$ opto-isolated relay board, active-LOW trigger, contacts rated $\ge 10\text{A} @ 250\text{V AC} / 30\text{V DC}$ | Standard Songle SRD-05VDC-SL-C module |
| **H6** | MicroSD Card | 1 | Class 10 / U3 MicroSD card, minimum $16\text{GB}$ capacity (High Endurance recommended for 24/7 logging) | SanDisk Max Endurance 32GB |
| **H7** | SBC Power Supply | 1 | Official Raspberry Pi Power Supply ($5.1\text{V} / 3.0\text{A}$ USB-C or $5.1\text{V} / 2.5\text{A}$ Micro-USB depending on Pi model) | Official Raspberry Pi 15.3W USB-C PSU |

---

## 2. Irrigation / Misting Subsystem (External Load)

*Note: Do NOT power pumps or solenoid valves directly from Raspberry Pi power rails.*

| Item | Component | Qty | Key Specifications / Notes |
| :--- | :--- | :--- | :--- |
| **M1** | Misting Pump or Solenoid Valve | 1 | $12\text{V DC}$ diaphragm high-pressure pump (e.g., MistKing, Aquatec) OR $12\text{V DC} / 24\text{V DC} / 120\text{V AC}$ normally closed (NC) solenoid valve |
| **M2** | External Load Power Supply | 1 | Dedicated DC power adapter matched to pump/solenoid voltage & current rating (e.g., $12\text{V DC} / 2\text{–}5\text{A}$) |
| **M3** | Flyback Diode (DC inductive loads) | 1 | 1N4001 or 1N4007 rectifier diode across inductive DC pump/solenoid coils to suppress voltage spikes |
| **M4** | Tubing & Misting Nozzles | — | $1/4\text{"}$ push-fit nylon/polyethylene tubing, bulkheads, and misting nozzles rated for pump pressure |

---

## 3. Wiring, Passive Components & Prototyping Consumables

| Item | Component | Qty | Specifications |
| :--- | :--- | :--- | :--- |
| **P1** | 1-Wire Bus Pull-Up Resistor | 1 | $4.7\text{k}\Omega$ metal film resistor, $1/4\text{W}$ ($\pm 1\%$) |
| **P2** | DHT22 Pull-Up Resistor | 1 | $10\text{k}\Omega$ resistor (required only if using bare 4-pin DHT22 rather than a 3-pin breakout PCB) |
| **P3** | Jumper Wires | 1 set | Male-to-Female and Female-to-Female DuPont jumper ribbons ($20\text{cm}$) |
| **P4** | Terminal Breakout or Proto Hat | 1 | Screw terminal GPIO expansion breakout HAT or compact mini breadboard |
| **P5** | Project Enclosure | 1 | Vented ABS enclosure for Raspberry Pi, relay, and wiring isolation |

---

## 4. Software & Operating System Requirements

### Host Environment
- **Operating System:** Raspberry Pi OS Lite or Desktop (32-bit or 64-bit), Debian Bullseye or Bookworm.
- **Python Runtime:** Python 3.9+ (pre-installed on Raspberry Pi OS).
- **Process Manager:** `systemd` (standard init system).

### Kernel Modules & Device Tree Overlays
- **1-Wire:** `w1-gpio` enabled on pin BCM 4 (`dtoverlay=w1-gpio,gpiopin=4`).
- **$I^2C$:** Hardware bus 1 enabled (`dtparam=i2c_arm=on`, kernel modules `i2c-bcm2835`, `i2c-dev`).

### APT Package Dependencies
```bash
python3
python3-pip
python3-dev
i2c-tools
libgpiod2
```

### Python Library Dependencies
| Package | Version | Purpose |
| :--- | :--- | :--- |
| `RPi.GPIO` | $\ge 0.7.0$ | Low-level GPIO pin driving and relay tri-state control |
| `adafruit-circuitpython-dht` | $\ge 3.7.0$ | Bit-banging signal decoder for DHT22 humidity data |
| `RPLCD` | $\ge 1.3.0$ | HD44780 character LCD controller driver over $I^2C$ |
| `smbus2` | $\ge 0.4.0$ | Pure Python $I^2C$ communication bus abstraction |
| `flask` | $\ge 2.0.0$ | Lightweight WSGI web server and JSON REST API backend |

---

## 5. Operational Constraints & Environmental Limits

1. **Raspberry Pi Ambient Conditions:**
   - Operating temperature range: $0^\circ\text{C}$ to $50^\circ\text{C}$.
   - The Pi and relay module must be mounted in a splash-proof junction box *outside* the humid enclosure.
2. **Sensor Exposure:**
   - **DS18B20:** IP68 waterproof probe tips; suitable for direct submersion or prolonged high-humidity placement in hot basking and cool zones.
   - **DHT22:** Splash-resistant only, not waterproof. Avoid direct spray from misting nozzles to prevent sensor element saturation and false $100\%$ readings.
3. **Electrical Isolation:**
   - The relay trigger side (`IN`, `VCC`, `GND`) connects to the Pi ($5\text{V}$ logic/coil).
   - The load side (`COM`, `NO`) must remain strictly isolated from all Raspberry Pi ground and voltage rails.