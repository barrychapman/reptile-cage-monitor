#!/usr/bin/env python3
import json
import os
import subprocess
from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

# Base directory & path setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONF_DIR = os.path.join(BASE_DIR, "conf")
SETTINGS_FILE = os.path.join(CONF_DIR, "settings.json")
STATUS_FILE = "/dev/shm/status.json"
COMMAND_FILE = "/dev/shm/command.json"

# Change this to your exact systemd service name if different
VIDEO_SERVICE_NAME = "lizcam.service"

os.makedirs(CONF_DIR, exist_ok=True)

STREAM_URL = "https://lizcam.ghosttown.io/live/stream/"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Cage Monitor Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
            max-width: 1200px; 
            margin: 20px auto; 
            padding: 0 15px; 
            background: #f4f6f8; 
            color: #333;
        }
        .header { margin-bottom: 20px; }
        .header h1 { margin: 0; font-size: 1.8rem; color: #222; }

        .layout-container {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
        }
        .video-column {
            flex: 1 1 550px;
            display: flex;
            flex-direction: column;
        }
        .controls-column {
            flex: 1 1 350px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .card { 
            background: white; 
            padding: 20px; 
            border-radius: 10px; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.08); 
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #edf2f7; 
            padding-bottom: 10px; 
            margin-bottom: 15px;
        }
        .card-header h2 { 
            margin: 0; 
            font-size: 1.3rem; 
        }

        .video-box {
            position: relative;
            width: 100%;
            background: #111;
            border-radius: 8px;
            overflow: hidden;
            aspect-ratio: 16 / 9;
            min-height: 380px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .video-box iframe {
            width: 100%;
            height: 100%;
            border: 0;
            display: block;
        }
        .video-offline-msg {
            color: #aaa;
            font-size: 1.1rem;
            text-align: center;
        }

        .val { font-size: 1.4rem; font-weight: bold; color: #007bff; }
        .val-hot { color: #d9534f; }
        .val-cool { color: #0275d8; }
        .val-hum { color: #28a745; }
        label { display: block; margin-top: 10px; font-weight: bold; font-size: 0.9rem; }
        input[type="number"], input[type="text"] { width: 100%; padding: 8px; margin: 6px 0; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        button { border: none; padding: 10px 15px; border-radius: 4px; cursor: pointer; width: 100%; font-size: 1rem; }
        .btn-save { background: #28a745; color: white; margin-top: 15px; }
        .btn-save:hover { background: #218838; }
        .btn-trigger { background: #007bff; color: white; margin-top: 10px; }
        .btn-trigger:hover { background: #0069d9; }
        .btn-stop { background: #dc3545; color: white; margin-top: 10px; }
        .btn-stop:hover { background: #c82333; }
        button:disabled { background: #a0aec0 !important; cursor: not-allowed; }
        .active { color: #28a745; }
        .cooling { color: #fd7e14; }
        .inactive { color: #6c757d; }
        .disabled-text { color: #e53e3e; }

        /* Master Toggle Switch */
        .master-switch-box {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #edf2f7;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .master-switch-box span { font-weight: bold; font-size: 1rem; }
        
        /* Toggle Switch Component */
        .switch {
            position: relative;
            display: inline-block;
            width: 46px;
            height: 24px;
        }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: #cbd5e0;
            transition: .3s;
            border-radius: 24px;
        }
        .slider:before {
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: .3s;
            border-radius: 50%;
        }
        input:checked + .slider { background-color: #28a745; }
        input:checked + .slider:before { transform: translateX(22px); }

        .service-badge {
            font-size: 0.85rem;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
            margin-right: 10px;
        }
        .service-running { background: #c6f6d5; color: #22543d; }
        .service-stopped { background: #fed7d7; color: #742a2a; }

        @media (max-width: 850px) {
            .layout-container { flex-direction: column; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Environment & Irrigation Control</h1>
    </div>

    <div class="layout-container">
        <!-- Live Video Column -->
        <div class="video-column">
            <div class="card" style="height: 100%;">
                <div class="card-header">
                    <h2>Live Enclosure Feed</h2>
                    <div style="display: flex; align-items: center;">
                        <span id="videoStatusBadge" class="service-badge service-stopped">Checking...</span>
                        <label class="switch">
                            <input type="checkbox" id="videoToggle" onchange="toggleVideoService(this.checked)">
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>
                <div class="video-box" id="videoWrapper">
                    <div class="video-offline-msg">Video Service Offline</div>
                </div>
            </div>
        </div>

        <!-- Telemetry & Controls Column -->
        <div class="controls-column">
            <div class="card">
                <div class="card-header">
                    <h2>Live Telemetry</h2>
                </div>

                <div class="master-switch-box">
                    <span>Irrigation Master Power</span>
                    <label class="switch">
                        <input type="checkbox" id="masterToggle" {% if settings.irrigation_enabled %}checked{% endif %} onchange="toggleMasterSwitch(this.checked)">
                        <span class="slider"></span>
                    </label>
                </div>

                <p>Hot Zone: <span id="tempHot" class="val val-hot">--</span> °F</p>
                <p>Cool Zone: <span id="tempCool" class="val val-cool">--</span> °F</p>
                <p>Humidity: <span id="hum" class="val val-hum">--</span> %</p>
                <p>Irrigation: <span id="relay" class="val">--</span></p>
                <button id="actionBtn" class="btn-trigger" onclick="handleAction()">Run Irrigation Now</button>
            </div>

            <div class="card">
                <div class="card-header">
                    <h2>System Configuration</h2>
                </div>
                <form method="POST" action="/update">
                    <label>Low Humidity Threshold (%):</label>
                    <input type="number" step="0.5" name="humidity_low" value="{{ settings.humidity_low }}" required>

                    <label>High Humidity Threshold (%):</label>
                    <input type="number" step="0.5" name="humidity_high" value="{{ settings.humidity_high }}" required>

                    <label>Max Run Duration (Seconds):</label>
                    <input type="number" step="1" name="max_run_seconds" value="{{ settings.max_run_seconds }}" required>

                    <label>Cooldown Duration (Seconds):</label>
                    <input type="number" step="1" name="cooldown_seconds" value="{{ settings.cooldown_seconds }}" required>

                    <label>Rolling Samples:</label>
                    <input type="number" step="1" name="smoothing_samples" value="{{ settings.smoothing_samples }}" required>

                    <label>Hot Zone Probe ID:</label>
                    <input type="text" name="hot_probe_id" value="{{ settings.hot_probe_id }}" required>

                    <label>Cool Zone Probe ID:</label>
                    <input type="text" name="cool_probe_id" value="{{ settings.cool_probe_id }}" required>

                    <button type="submit" class="btn-save">Save Settings</button>
                </form>
            </div>
        </div>
    </div>

    <script>
        const STREAM_URL = "{{ stream_url }}";
        let currentMode = "start";
        let isVideoActive = false;

        function checkVideoStatus() {
            fetch('/api/video/status')
                .then(r => r.json())
                .then(data => {
                    const badge = document.getElementById('videoStatusBadge');
                    const toggle = document.getElementById('videoToggle');
                    const wrapper = document.getElementById('videoWrapper');

                    if (data.active) {
                        badge.className = 'service-badge service-running';
                        badge.innerText = 'Online';
                        toggle.checked = true;

                        if (!isVideoActive) {
                            wrapper.innerHTML = `<iframe src="${STREAM_URL}" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe>`;
                            isVideoActive = true;
                        }
                    } else {
                        badge.className = 'service-badge service-stopped';
                        badge.innerText = 'Offline';
                        toggle.checked = false;

                        if (isVideoActive) {
                            wrapper.innerHTML = '<div class="video-offline-msg">Video Service Offline</div>';
                            isVideoActive = false;
                        }
                    }
                })
                .catch(() => {});
        }

        function toggleVideoService(enable) {
            const toggle = document.getElementById('videoToggle');
            toggle.disabled = true;

            fetch(enable ? '/api/video/start' : '/api/video/stop', { method: 'POST' })
                .then(r => r.json())
                .then(() => {
                    setTimeout(() => {
                        checkVideoStatus();
                        toggle.disabled = false;
                    }, 1200);
                })
                .catch(() => {
                    toggle.disabled = false;
                });
        }

        function toggleMasterSwitch(enabled) {
            fetch('/api/toggle_master', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: enabled })
            }).then(() => fetchStatus());
        }

        function fetchStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('tempHot').innerText = (data.temp_hot !== null && data.temp_hot !== undefined) ? data.temp_hot : '--';
                    document.getElementById('tempCool').innerText = (data.temp_cool !== null && data.temp_cool !== undefined) ? data.temp_cool : '--';
                    document.getElementById('hum').innerText = (data.humidity !== null && data.humidity !== undefined) ? data.humidity : '--';
                    const rEl = document.getElementById('relay');
                    const btn = document.getElementById('actionBtn');
                    const masterToggle = document.getElementById('masterToggle');
                    
                    rEl.innerText = data.relay_state;

                    if (data.relay_state === 'Disabled') {
                        rEl.className = 'val disabled-text';
                        btn.className = 'btn-trigger';
                        btn.innerText = 'Irrigation Disabled';
                        btn.disabled = true;
                    } else if (data.relay_state.startsWith('Active')) {
                        rEl.className = 'val active';
                        btn.className = 'btn-stop';
                        btn.innerText = 'Stop Irrigation Now';
                        btn.disabled = false;
                        currentMode = "stop";
                    } else if (data.relay_state.startsWith('Cooling')) {
                        rEl.className = 'val cooling';
                        btn.className = 'btn-trigger';
                        btn.innerText = 'Force Run Irrigation Now';
                        btn.disabled = !masterToggle.checked;
                        currentMode = "start";
                    } else {
                        rEl.className = 'val inactive';
                        btn.className = 'btn-trigger';
                        btn.innerText = 'Run Irrigation Now';
                        btn.disabled = !masterToggle.checked;
                        currentMode = "start";
                    }
                })
                .catch(() => {});
        }

        function handleAction() {
            const btn = document.getElementById('actionBtn');
            btn.disabled = true;
            const endpoint = currentMode === "stop" ? "/api/manual_stop" : "/api/manual_trigger";
            
            fetch(endpoint, { method: 'POST' })
                .then(() => fetchStatus())
                .catch(() => {});
        }

        setInterval(fetchStatus, 2000);
        setInterval(checkVideoStatus, 5000);

        fetchStatus();
        checkVideoStatus();
    </script>
</body>
</html>
"""

def is_service_active(service_name):
    cmd = ["sudo", "systemctl", "is-active", "--quiet", service_name]
    ret = subprocess.run(cmd)
    return ret.returncode == 0

def run_service_command(action, service_name):
    cmd = ["sudo", "systemctl", action, service_name]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode == 0

def get_current_settings():
    settings = {
        "humidity_low": 63.0,
        "humidity_high": 75.0,
        "smoothing_samples": 5,
        "max_run_seconds": 10,
        "cooldown_seconds": 120,
        "irrigation_enabled": True,
        "hot_probe_id": "28-000000cab2e9",
        "cool_probe_id": "28-000000caa4ee"
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings.update(json.load(f))
        except Exception:
            pass
    return settings

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, settings=get_current_settings(), stream_url=STREAM_URL)

@app.route("/api/status")
def get_status():
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r") as f:
                return jsonify(json.load(f))
        except Exception:
            pass
    return jsonify({
        "temp_hot": None,
        "temp_cool": None,
        "humidity": None,
        "relay_state": "Offline"
    })

# Video Service Endpoints
@app.route("/api/video/status")
def video_status():
    return jsonify({"active": is_service_active(VIDEO_SERVICE_NAME), "service": VIDEO_SERVICE_NAME})

@app.route("/api/video/start", methods=["POST"])
def video_start():
    success = run_service_command("start", VIDEO_SERVICE_NAME)
    return jsonify({"success": success, "active": is_service_active(VIDEO_SERVICE_NAME)})

@app.route("/api/video/stop", methods=["POST"])
def video_stop():
    success = run_service_command("stop", VIDEO_SERVICE_NAME)
    return jsonify({"success": success, "active": is_service_active(VIDEO_SERVICE_NAME)})

@app.route("/api/toggle_master", methods=["POST"])
def toggle_master():
    data = request.get_json() or {}
    enabled = bool(data.get("enabled", True))
    
    settings = get_current_settings()
    settings["irrigation_enabled"] = enabled
    
    tmp_path = f"{SETTINGS_FILE}.tmp"
    with open(tmp_path, "w") as f:
        json.dump(settings, f, indent=2)
    os.replace(tmp_path, SETTINGS_FILE)
    return jsonify({"success": True, "irrigation_enabled": enabled})

@app.route("/api/manual_trigger", methods=["POST"])
def manual_trigger():
    settings = get_current_settings()
    if not settings.get("irrigation_enabled", True):
        return jsonify({"success": False, "error": "System is disabled"}), 400

    tmp_path = f"{COMMAND_FILE}.tmp"
    with open(tmp_path, "w") as f:
        json.dump({"action": "start_irrigation"}, f)
    os.replace(tmp_path, COMMAND_FILE)
    return jsonify({"success": True})

@app.route("/api/manual_stop", methods=["POST"])
def manual_stop():
    tmp_path = f"{COMMAND_FILE}.tmp"
    with open(tmp_path, "w") as f:
        json.dump({"action": "stop_irrigation"}, f)
    os.replace(tmp_path, COMMAND_FILE)
    return jsonify({"success": True})

@app.route("/update", methods=["POST"])
def update_settings():
    settings = get_current_settings()
    settings.update({
        "humidity_low": float(request.form.get("humidity_low", 63.0)),
        "humidity_high": float(request.form.get("humidity_high", 75.0)),
        "max_run_seconds": int(request.form.get("max_run_seconds", 10)),
        "cooldown_seconds": int(request.form.get("cooldown_seconds", 120)),
        "smoothing_samples": int(request.form.get("smoothing_samples", 5)),
        "hot_probe_id": request.form.get("hot_probe_id", settings.get("hot_probe_id", "")).strip(),
        "cool_probe_id": request.form.get("cool_probe_id", settings.get("cool_probe_id", "")).strip()
    })
    tmp_path = f"{SETTINGS_FILE}.tmp"
    with open(tmp_path, "w") as f:
        json.dump(settings, f, indent=2)
    os.replace(tmp_path, SETTINGS_FILE)
    return index()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)