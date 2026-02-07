"""Capture screenshots with full emulator UI for each device.

Runs each demo app with pygame's dummy video driver, waits for
the first frame to render, then saves the full window as a screenshot.
"""

import subprocess
import sys
import time
import os

APPS = [
    ("tufty", "apps/tufty/hello_badge.py"),
    ("presto", "apps/presto/touch_demo.py"),
    ("badger", "apps/badger/hello_badge.py"),
    ("inky_frame", "apps/inky_frame/hello_inky.py"),
    ("inky_impression", "apps/inky_impression/hello_impression.py"),
]

SCREENSHOT_DIR = "screenshots"

HELPER_TEMPLATE = '''
import sys, os, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())

from emulator import _emulator_state
from emulator.devices import get_device
from emulator.display import create_display
from emulator.hardware.buttons import ButtonManager
from emulator.hardware.touch import TouchManager
from emulator.hardware.sensors import SensorManager
from emulator.hardware.wifi import WiFiManager
from emulator.mocks import install_mocks, install_inky_mocks, install_badgeware_mocks, setup_vfs
import runpy, threading
from pathlib import Path

device = get_device("{device}")
_emulator_state["device"] = device
_emulator_state["running"] = True
_emulator_state["headless"] = False
_emulator_state["trace"] = False
_emulator_state["max_frames"] = 0

library_type = getattr(device, "library_type", None)
if library_type == "inky":
    install_inky_mocks()
elif library_type == "badgeware":
    install_badgeware_mocks()
else:
    install_mocks()

if "badger" in "{app}".lower():
    setup_vfs("{app}")

display = create_display(device, headless=False)
_emulator_state["display"] = display
display.init()

button_manager = ButtonManager(device)
touch_manager = TouchManager(device)
sensor_manager = SensorManager(device)

app_path = Path("{app}")

def app_thread():
    try:
        app_dir = str(app_path.parent.absolute())
        if app_dir not in sys.path:
            sys.path.insert(0, app_dir)
        runpy.run_path(str(app_path), run_name="__main__")
    except Exception:
        pass
    finally:
        _emulator_state["running"] = False

thread = threading.Thread(target=app_thread, daemon=True)
thread.start()

import pygame

# Wait for first frame
for _ in range(200):
    for event in pygame.event.get():
        pass
    if display.get_frame_count() > 0:
        break
    time.sleep(0.05)

# Let it settle
time.sleep(0.3)
for event in pygame.event.get():
    pass

# Save full window screenshot
if display._window:
    pygame.image.save(display._window, "{output}")
    print("OK")
else:
    print("FAIL: no window")

_emulator_state["running"] = False
thread.join(timeout=1.0)
display.close()
'''


def main():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    for device, app in APPS:
        output = os.path.join(SCREENSHOT_DIR, f"{device}.png")
        print(f"Capturing {device}...", end=" ")
        helper = HELPER_TEMPLATE.format(device=device, app=app, output=output)
        try:
            proc = subprocess.run(
                [sys.executable, "-c", helper],
                timeout=30,
                capture_output=True,
                text=True,
                env={**os.environ, "SDL_VIDEODRIVER": "dummy"},
            )
            # Print last meaningful line
            for line in proc.stdout.strip().splitlines():
                if line.strip():
                    print(line.strip())
            if proc.returncode != 0:
                for line in proc.stderr.splitlines():
                    if "error" in line.lower() or "Error" in line:
                        print(f"  {line.strip()}")
        except subprocess.TimeoutExpired:
            print("TIMEOUT")
        except Exception as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    main()
