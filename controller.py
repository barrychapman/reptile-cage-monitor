#!/usr/bin/env python3
import os
import signal
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MONITOR_SCRIPT = os.path.join(BASE_DIR, "system_monitor.py")
WEBSERVER_SCRIPT = os.path.join(BASE_DIR, "web_server.py")

p_monitor = None
p_web = None
shutting_down = False

def shutdown_processes(signum=None, frame=None):
    global shutting_down
    if shutting_down:
        return
    shutting_down = True

    print("\n[Controller] Shutdown initiated. Stopping monitor and web server...")

    # 1. Stop Web Server first
    if p_web and p_web.poll() is None:
        try:
            p_web.terminate()
            p_web.wait(timeout=3.0)
            print("[Controller] Web server stopped cleanly.")
        except subprocess.TimeoutExpired:
            print("[Controller] Web server timed out; forcing kill.")
            p_web.kill()
        except OSError:
            pass

    # 2. Stop Monitor with SIGINT/SIGTERM so it runs GPIO.cleanup() and clears LCD
    if p_monitor and p_monitor.poll() is None:
        try:
            # If shutdown was triggered by systemd (SIGTERM), send SIGTERM to child
            sig_to_send = signal.SIGINT if signum == signal.SIGINT else signal.SIGTERM
            p_monitor.send_signal(sig_to_send)
        except OSError:
            pass

        try:
            p_monitor.wait(timeout=4.0)
            print("[Controller] Monitor exited cleanly.")
        except subprocess.TimeoutExpired:
            print("[Controller] Monitor timed out during cleanup; forcing termination.")
            p_monitor.kill()
        except OSError:
            pass

    print("[Controller] All sub-processes stopped.")
    sys.exit(0)

# Register signals for interactive (SIGINT) and systemd (SIGTERM)
signal.signal(signal.SIGINT, shutdown_processes)
signal.signal(signal.SIGTERM, shutdown_processes)

def main():
    global p_monitor, p_web
    print("[Controller] Launching System Monitor and Web Server supervisor...")

    if not os.path.isfile(MONITOR_SCRIPT):
        print(f"[Controller] Error: {MONITOR_SCRIPT} not found.")
        sys.exit(1)
    if not os.path.isfile(WEBSERVER_SCRIPT):
        print(f"[Controller] Error: {WEBSERVER_SCRIPT} not found.")
        sys.exit(1)

    # Launch child daemons with unbuffered output
    p_monitor = subprocess.Popen(
        [sys.executable, "-u", MONITOR_SCRIPT],
        cwd=BASE_DIR
    )

    p_web = subprocess.Popen(
        [sys.executable, "-u", WEBSERVER_SCRIPT],
        cwd=BASE_DIR
    )

    try:
        while True:
            # Guard against unhandled crashes in either child process
            ret_monitor = p_monitor.poll()
            if ret_monitor is not None:
                print(f"[Controller] System Monitor exited unexpectedly (code: {ret_monitor}).")
                break

            ret_web = p_web.poll()
            if ret_web is not None:
                print(f"[Controller] Web Server exited unexpectedly (code: {ret_web}).")
                break

            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        shutdown_processes()

if __name__ == "__main__":
    main()