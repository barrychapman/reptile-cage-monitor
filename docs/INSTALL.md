# Installation & Deployment Guide

This guide walks through setting up the Raspberry Pi from an active OS install to fully functional hardware telemetry, display output, web control, and automated background supervisor management.

---

## 1. Prerequisites & Base System Setup

1. Boot your Raspberry Pi with Raspberry Pi OS (Bullseye or Bookworm).
2. Connect to the Pi via SSH or local terminal.
3. Bring the package manager up to date:

```bash
sudo apt update && sudo apt upgrade -y
```

---

## 2. Enable Hardware Buses (I2C & 1-Wire)

The system requires both the I2C bus (for the 20x4 LCD backpack) and the 1-Wire bus (on GPIO 4 for the DS18B20 temperature probes).

### Automatic Activation
Run the non-interactive configuration tool:

```bash
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_onewire 0
```

### Verify Boot Config
Depending on your OS version, the boot configuration resides at `/boot/config.txt` (Bullseye/legacy) or `/boot/firmware/config.txt` (Bookworm).

Open the active configuration:

```bash
sudo nano /boot/config.txt
```
*(On Bookworm, edit `/boot/firmware/config.txt` instead).*

Ensure the following parameters are present under the `[all]` section (or at the top of the file):

```ini
dtparam=i2c_arm=on
dtoverlay=w1-gpio,gpiopin=4
```

Reboot the Raspberry Pi to initialize the hardware overlays:

```bash
sudo reboot
```

---

## 3. Install System & Python Dependencies

Install the core C libraries, I2C discovery tools, and Python build headers:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-dev i2c-tools libgpiod2
```

Install the required Python packages globally so they are available to root systemd daemons:

```bash
sudo pip3 install \
  RPi.GPIO \
  adafruit-circuitpython-dht \
  RPLCD \
  smbus2 \
  flask
```

---

## 4. Hardware Verification & Sensor Discovery

Before setting up background services, test every sensor individually.

### Check I2C LCD Detection
Verify that the PCF8574 I2C backpack is visible on I2C bus 1:

```bash
sudo i2cdetect -y 1
```

You should see `27` (or `3f`) populated in the grid. If the address is `0x3f`, update `LCD_ADDRESS` in `system_monitor.py` accordingly.

### Discover DS18B20 1-Wire Probe IDs
Check the 1-Wire device registry:

```bash
ls -la /sys/bus/w1/devices/
```

You will see directories starting with `28-` (e.g., `28-000000cab2e9` and `28-000000caa4ee`).

To determine which probe goes into the Hot Zone vs. Cool Zone:
1. Hold one probe tip tightly between your fingers for 10 seconds.
2. Read both probes:
   ```bash
   cat /sys/bus/w1/devices/28-000000cab2e9/w1_slave
   cat /sys/bus/w1/devices/28-000000caa4ee/w1_slave
   ```
3. Look at the `t=XXXXX` string on line 2 (e.g., `t=29312` is 29.31°C / 84.8°F). The ID with the elevated temperature is the physical probe in your hand.

### Test DHT22 Sensor on GPIO 22
Verify the DHT22 reads humidity and temperature cleanly:

```bash
python3 -c "import board, adafruit_dht; d = adafruit_dht.DHT22(board.D22, use_pulseio=False); print('Humidity:', d.humidity, 'Temp:', d.temperature)"
```

---

## 5. Application Deployment

Create the operational directories and move the scripts into place:

```bash
sudo mkdir -p /opt/scripts/conf /opt/scripts/docs
sudo chown -R $USER:$USER /opt/scripts
```

Place `controller.py`, `system_monitor.py`, and `web_server.py` into `/opt/scripts/`, and make all three executable:

```bash
chmod +x /opt/scripts/controller.py
chmod +x /opt/scripts/system_monitor.py
chmod +x /opt/scripts/web_server.py
```

Create `/opt/scripts/conf/settings.json` and insert your discovered DS18B20 serial numbers:

```bash
cat << 'EOF' > /opt/scripts/conf/settings.json
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
EOF
```

---

## 6. Configure Unified Supervisor Service

`controller.py` acts as the single master process supervisor, managing the lifecycle of both `system_monitor.py` and `web_server.py` as child processes. Only one systemd unit is needed.

Create `/etc/systemd/system/cage-controller.service`:

```bash
sudo nano /etc/systemd/system/cage-controller.service
```

Paste the following unit configuration:

```ini
[Unit]
Description=Cage Environment Monitor & Web Supervisor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/scripts
ExecStart=/usr/bin/python3 /opt/scripts/controller.py
Restart=always
RestartSec=5
KillSignal=SIGTERM
TimeoutStopSec=15

[Install]
WantedBy=multi-user.target
```

---

## 7. Service Enablement & Final Verification

1. If the legacy separate `cage-web.service` exists on your system, disable and remove it to avoid port collisions:
   ```bash
   sudo systemctl stop cage-web.service 2>/dev/null || true
   sudo systemctl disable cage-web.service 2>/dev/null || true
   sudo rm -f /etc/systemd/system/cage-web.service
   ```

2. Reload systemd to index the updated supervisor unit definition:
   ```bash
   sudo systemctl daemon-reload
   ```

3. Enable and start the consolidated supervisor service:
   ```bash
   sudo systemctl enable --now cage-controller.service
   ```

4. Confirm the supervisor is running and has spawned both child daemons:
   ```bash
   systemctl status cage-controller.service
   ```

5. Inspect aggregated supervisor logs:
   ```bash
   sudo journalctl -u cage-controller.service -f
   ```

6. Verify that shared memory telemetry is actively publishing:
   ```bash
   cat /dev/shm/status.json
   ```

7. Access the Web Dashboard:
   Open a browser on your local network and navigate to:
   ```text
   http://<YOUR_PI_IP_ADDRESS>:5000
   ```