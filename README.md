# Enclosure Environmental Monitor & Automated Irrigation Controller

An automated telemetry, environmental control, and misting system for reptile and animal enclosures powered by a Raspberry Pi. The system provides continuous monitoring of a dual-zone thermal gradient (Hot/Basking and Cool zones), relative humidity tracking, local status readout via an LCD, and a browser-based dashboard with live video stream controls and threshold configuration.

## Features

* **Dual-Zone Thermal Monitoring:** Simultaneous tracking of hot and cool zones using two Dallas DS18B20 1-Wire waterproof digital probes.
* **Humidity Management:** Continuous relative humidity measurement via an Adafruit DHT22 sensor with moving-average filtering.
* **Automated Irrigation Control:** Hysteresis-based relay automation with safety run-time limits, minimum cooldown intervals, and high-impedance safe pin driving.
* **Local Character Display:** 20x4 I2C LCD showing real-time temperatures, humidity, and relay status.
* **Web Dashboard & REST API:** Responsive Flask web interface providing live sensor telemetry, manual run/stop overrides, threshold setpoint adjustments, and embedded camera streaming (`lizcam.service` management).
* **Unified Process Supervisor:** A master supervisor daemon (`controller.py`) manages both `system_monitor.py` and `web_server.py`, orchestrating graceful child shutdowns, hardware cleanup, and crash restarts under a single systemd unit.
* **Decoupled Daemon Architecture:** Inter-process communication via Linux shared memory (`/dev/shm`), allowing the hardware controller and web server to operate and restart independently.

## System Overview & Pin Reference

| Peripheral | Interface / Pin | Physical Pin | Description |
| :--- | :--- | :--- | :--- |
| **DS18B20 (Hot Zone)** | 1-Wire Data (`GPIO 4`) | Pin 7 | Shared bus with $4.7\text{ k}\Omega$ pull-up to $3.3\text{ V}$ |
| **DS18B20 (Cool Zone)** | 1-Wire Data (`GPIO 4`) | Pin 7 | Shared bus with $4.7\text{ k}\Omega$ pull-up to $3.3\text{ V}$ |
| **DHT22** | Dedicated Data (`GPIO 22`) | Pin 15 | Dedicated GPIO line for humidity sensing |
| **Relay Module** | Trigger Input (`GPIO 17`) | Pin 11 | Active-LOW control for misting pump / solenoid |
| **20x4 LCD (PCF8574)** | I2C SDA (`GPIO 2`) | Pin 3 | Serial Data |
| **20x4 LCD (PCF8574)** | I2C SCL (`GPIO 3`) | Pin 5 | Serial Clock |

## Repository Structure

```
├── conf/
│   └── settings.json          # Operational setpoints, timings, and probe IDs
├── docs/
│   ├── HARDWARE_SETUP.md      # Comprehensive wiring schematics and electrical guide
│   ├── INSTALL.md             # Step-by-step OS, library, and systemd deployment guide
│   └── REQUIREMENTS.md        # Hardware bill of materials and software dependencies
├── controller.py              # Unified supervisor: manages monitor & web server lifecycle
├── system_monitor.py          # Hardware monitoring daemon, LCD driver & relay logic
├── web_server.py              # Flask web dashboard, REST API & camera controls
└── README.md                  # Project overview and reference
```

## Quick Start

### 1. Enable Hardware Interfaces

Ensure I2C and 1-Wire are enabled in `/boot/config.txt` (or `/boot/firmware/config.txt` on Bookworm):

```bash
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_onewire 0
```

Verify the boot config contains:

```ini
dtparam=i2c_arm=on
dtoverlay=w1-gpio,gpiopin=4
```

### 2. Install Dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-dev i2c-tools libgpiod2

sudo pip3 install RPi.GPIO adafruit-circuitpython-dht RPLCD smbus2 flask
```

### 3. Configure Probe IDs

Identify your probe IDs under `/sys/bus/w1/devices/` and update `conf/settings.json`:

```json
{
  "humidity_low": 63.0,
  "humidity_high": 75.0,
  "smoothing_samples": 5,
  "max_run_seconds": 10,
  "cooldown_seconds": 120,
  "irrigation_enabled": true,
  "hot_probe_id": "28-000000cab2e9",
  "cool_probe_id": "28-000000caa4ee"
}
```

### 4. Run Supervisor Service

Deploy the unified `cage-controller.service` (which executes `controller.py` to supervise both sub-processes):

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cage-controller.service
```

Access the dashboard at `http://<PI_IP_ADDRESS>:5000`.

## Documentation Links

* **Wiring & Electrical:** See [docs/HARDWARE_SETUP.md](docs/HARDWARE_SETUP.md) for schematics, resistor sizing, and relay isolation details.
* **Installation & Deployment:** See [docs/INSTALL.md](docs/INSTALL.md) for full OS setup, hardware testing, and systemd service configuration.
* **Bill of Materials & Specs:** See [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) for part numbers, specifications, and external load guidelines.

## License

This project is open-source and available under the [MIT License](LICENSE).