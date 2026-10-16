#!/usr/bin/env python3
import json
import os
import signal
import sys
import time
from collections import deque
import board
import adafruit_dht
import RPi.GPIO as GPIO
from RPLCD.i2c import CharLCD

# --- HARDWARE PINS & BUS CONFIGURATION ---
RELAY_PIN = 17           # Physical Pin 11 (GPIO 17)
DHT_PIN = board.D22      # Physical Pin 15 (GPIO 22)
LCD_ADDRESS = 0x27       # Detected I2C address for PCF8574

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "conf", "settings.json")
STATUS_FILE = "/dev/shm/status.json"
COMMAND_FILE = "/dev/shm/command.json"
W1_DIR = "/sys/bus/w1/devices"

# Default fallback values
HUMIDITY_LOW = 63.0
HUMIDITY_HIGH = 75.0
SMOOTHING_SAMPLES = 5
MAX_RUN_SECONDS = 10
COOLDOWN_SECONDS = 120
IRRIGATION_ENABLED = True
HOT_PROBE_ID = "28-000000cab2e9"
COOL_PROBE_ID = "28-000000caa4ee"

irrigation_start_time = 0.0
cooldown_start_time = 0.0

lcd = CharLCD(i2c_expander='PCF8574', address=LCD_ADDRESS, port=1, cols=20, rows=4)
dht_sensor = adafruit_dht.DHT22(DHT_PIN, use_pulseio=False)

hum_history = deque(maxlen=SMOOTHING_SAMPLES)
hot_temp_history = deque(maxlen=SMOOTHING_SAMPLES)
cool_temp_history = deque(maxlen=SMOOTHING_SAMPLES)

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

def set_relay(state):
    """Controls active-low relay safely using high-impedance input for release."""
    if state == "engage":
        GPIO.setup(RELAY_PIN, GPIO.OUT)
        GPIO.output(RELAY_PIN, GPIO.LOW)
    elif state == "release":
        GPIO.setup(RELAY_PIN, GPIO.IN)

def format_line(text):
    return f"{text[:20]:<20}"

def read_ds18b20(device_id):
    """Reads temperature in Fahrenheit from 1-Wire sysfs interface."""
    if not device_id:
        return None
    device_file = os.path.join(W1_DIR, device_id, "w1_slave")
    if not os.path.exists(device_file):
        return None
    try:
        with open(device_file, "r") as f:
            lines = f.readlines()
        if len(lines) >= 2 and "YES" in lines[0]:
            pos = lines[1].find("t=")
            if pos != -1:
                temp_c = float(lines[1][pos + 2:]) / 1000.0
                return (temp_c * 9.0 / 5.0) + 32.0
    except Exception:
        pass
    return None

def update_screen(hot_t, cool_t, hum, relay_state):
    """Writes dual temperatures, humidity, and relay status to the 20x4 LCD."""
    try:
        lcd.cursor_pos = (0, 0)
        lcd.write_string(format_line("Enclosure Monitor"))

        hot_str = f"{hot_t:.1f}" if hot_t is not None else "--"
        cool_str = f"{cool_t:.1f}" if cool_t is not None else "--"
        lcd.cursor_pos = (1, 0)
        lcd.write_string(format_line(f"H:{hot_str}F  C:{cool_str}F"))

        lcd.cursor_pos = (2, 0)
        if hum is not None:
            lcd.write_string(format_line(f"Humidity: {hum:5.1f} %"))
        else:
            lcd.write_string(format_line("Humidity: Reading"))

        # Accurately report active relay status even with timer strings attached
        if relay_state.startswith("Active"):
            relay_msg = "ON"
        elif relay_state == "Disabled":
            relay_msg = "DISABLED"
        elif relay_state.startswith("Cooldown"):
            relay_msg = "COOLDOWN"
        else:
            relay_msg = "OFF"

        lcd.cursor_pos = (3, 0)
        lcd.write_string(format_line(f"Irrigation: {relay_msg}"))
    except OSError as e:
        if e.errno == 121:
            time.sleep(0.05)

def load_settings():
    global HUMIDITY_LOW, HUMIDITY_HIGH, SMOOTHING_SAMPLES, MAX_RUN_SECONDS, COOLDOWN_SECONDS
    global IRRIGATION_ENABLED, HOT_PROBE_ID, COOL_PROBE_ID, hum_history
    if not os.path.exists(SETTINGS_FILE):
        return

    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
            HUMIDITY_LOW = float(data.get("humidity_low", HUMIDITY_LOW))
            HUMIDITY_HIGH = float(data.get("humidity_high", HUMIDITY_HIGH))
            MAX_RUN_SECONDS = int(data.get("max_run_seconds", MAX_RUN_SECONDS))
            COOLDOWN_SECONDS = int(data.get("cooldown_seconds", COOLDOWN_SECONDS))
            IRRIGATION_ENABLED = bool(data.get("irrigation_enabled", True))
            HOT_PROBE_ID = data.get("hot_probe_id", HOT_PROBE_ID)
            COOL_PROBE_ID = data.get("cool_probe_id", COOL_PROBE_ID)
            
            new_samples = int(data.get("smoothing_samples", SMOOTHING_SAMPLES))
            if new_samples != SMOOTHING_SAMPLES and new_samples > 0:
                SMOOTHING_SAMPLES = new_samples
                hum_history = deque(hum_history, maxlen=SMOOTHING_SAMPLES)
    except Exception:
        pass

def check_manual_command():
    if os.path.exists(COMMAND_FILE):
        try:
            with open(COMMAND_FILE, "r") as f:
                cmd = json.load(f)
            os.remove(COMMAND_FILE)
            return cmd.get("action")
        except Exception:
            try:
                os.remove(COMMAND_FILE)
            except OSError:
                pass
    return None

def save_status(hot_t, cool_t, hum, relay_state, time_remaining):
    payload = {
        "timestamp": time.time(),
        "temp_hot": round(hot_t, 1) if hot_t is not None else None,
        "temp_cool": round(cool_t, 1) if cool_t is not None else None,
        "humidity": round(hum, 1) if hum is not None else None,
        "relay_state": relay_state,
        "time_remaining_seconds": max(0, int(time_remaining)),
        "master_enabled": IRRIGATION_ENABLED
    }
    tmp_path = f"{STATUS_FILE}.tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(payload, f)
        os.replace(tmp_path, STATUS_FILE)
    except Exception:
        pass

# Ensure systemd termination signals trigger a clean exit
def handle_sigterm(signum, frame):
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)

current_relay_state = "Wait"
set_relay("release")
lcd.clear()
update_screen(None, None, None, current_relay_state)

time.sleep(2)
humidity = None
temp_hot = None
temp_cool = None

try:
    while True:
        load_settings()
        now = time.time()
        manual_cmd = check_manual_command()

        # Read DHT22 on GPIO 22
        try:
            raw_h = dht_sensor.humidity
            if raw_h is not None and 0.0 <= raw_h <= 100.0:
                hum_history.append(raw_h)
                humidity = sum(hum_history) / len(hum_history)
        except RuntimeError:
            pass

        # Read DS18B20 Probes
        raw_hot = read_ds18b20(HOT_PROBE_ID)
        if raw_hot is not None:
            hot_temp_history.append(raw_hot)
            temp_hot = sum(hot_temp_history) / len(hot_temp_history)

        raw_cool = read_ds18b20(COOL_PROBE_ID)
        if raw_cool is not None:
            cool_temp_history.append(raw_cool)
            temp_cool = sum(cool_temp_history) / len(cool_temp_history)

        # Handle Manual Commands from Web Interface
        if manual_cmd == "start_irrigation" and IRRIGATION_ENABLED and current_relay_state != "Active":
            set_relay("engage")
            current_relay_state = "Active"
            irrigation_start_time = now
            cooldown_start_time = 0.0

        elif manual_cmd == "stop_irrigation" and current_relay_state == "Active":
            set_relay("release")
            current_relay_state = "Cooldown"
            cooldown_start_time = now

        time_remaining = 0
        display_state = current_relay_state

        if not IRRIGATION_ENABLED:
            if current_relay_state == "Active":
                set_relay("release")
            current_relay_state = "Disabled"
            display_state = "Disabled"

        elif len(hum_history) < SMOOTHING_SAMPLES and current_relay_state != "Active":
            current_relay_state = "Initializing"
            display_state = "Initializing"

        elif current_relay_state == "Active":
            elapsed_run = now - irrigation_start_time
            time_remaining = MAX_RUN_SECONDS - elapsed_run

            if elapsed_run >= MAX_RUN_SECONDS or (humidity is not None and humidity > HUMIDITY_HIGH):
                set_relay("release")
                current_relay_state = "Cooldown"
                cooldown_start_time = now
                display_state = f"Cooldown ({COOLDOWN_SECONDS}s)"
            else:
                display_state = f"Active ({int(time_remaining)}s)"

        elif current_relay_state == "Cooldown":
            elapsed_cooldown = now - cooldown_start_time
            time_remaining = COOLDOWN_SECONDS - elapsed_cooldown

            if elapsed_cooldown >= COOLDOWN_SECONDS:
                current_relay_state = "Inactive"
                display_state = "Inactive"
            else:
                display_state = f"Cooldown ({int(time_remaining)}s)"

        else:
            if humidity is not None and humidity < HUMIDITY_LOW:
                set_relay("engage")
                current_relay_state = "Active"
                irrigation_start_time = now
                display_state = f"Active ({MAX_RUN_SECONDS}s)"
            else:
                current_relay_state = "Inactive"
                display_state = "Inactive"

        update_screen(temp_hot, temp_cool, humidity, display_state)
        save_status(temp_hot, temp_cool, humidity, display_state, time_remaining)
        time.sleep(2)

except (KeyboardInterrupt, SystemExit):
    set_relay("release")
    lcd.clear()
    dht_sensor.exit()
    GPIO.cleanup()