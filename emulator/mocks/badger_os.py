"""Mock implementation of badger_os module.

Provides state management and app launching utilities for Badger 2040.
"""

import os
import json
from pathlib import Path
from emulator import get_state


# State storage directory (in emulator, use a temp location)
STATE_DIR = "/tmp/badger_os_state"


def _ensure_state_dir():
    """Ensure state directory exists."""
    Path(STATE_DIR).mkdir(parents=True, exist_ok=True)


def state_load(app_name: str, state_dict: dict):
    """Load saved state for an app into the provided dict."""
    _ensure_state_dir()
    state_file = Path(STATE_DIR) / f"{app_name}.json"

    if state_file.exists():
        try:
            with open(state_file, "r") as f:
                loaded = json.load(f)
                state_dict.update(loaded)
        except (json.JSONDecodeError, IOError):
            pass

    emulator_state = get_state()
    if emulator_state.get("trace"):
        print(f"[badger_os] state_load({app_name}): {state_dict}")


def state_save(app_name: str, state_dict: dict):
    """Save app state."""
    _ensure_state_dir()
    state_file = Path(STATE_DIR) / f"{app_name}.json"

    try:
        with open(state_file, "w") as f:
            json.dump(state_dict, f)
    except IOError:
        pass

    emulator_state = get_state()
    if emulator_state.get("trace"):
        print(f"[badger_os] state_save({app_name}): {state_dict}")


def state_modify(app_name: str, key: str, value):
    """Modify a single value in app state."""
    state = {}
    state_load(app_name, state)
    state[key] = value
    state_save(app_name, state)


def state_launch():
    """Launch the previously running app (restore from state)."""
    _ensure_state_dir()
    running_file = Path(STATE_DIR) / "running.txt"

    if running_file.exists():
        try:
            with open(running_file, "r") as f:
                app = f.read().strip()
                if app and app != "launcher":
                    launch(app)
        except IOError:
            pass


def state_clear_running() -> bool:
    """Clear the running app state."""
    _ensure_state_dir()
    running_file = Path(STATE_DIR) / "running.txt"

    existed = running_file.exists()
    try:
        running_file.unlink(missing_ok=True)
    except IOError:
        pass

    return existed


def state_set_running(app_name: str):
    """Set the currently running app."""
    _ensure_state_dir()
    running_file = Path(STATE_DIR) / "running.txt"

    try:
        with open(running_file, "w") as f:
            f.write(app_name)
    except IOError:
        pass


def get_disk_usage():
    """Get disk usage statistics.

    Returns: (total_bytes, used_percent, free_bytes)
    """
    # Return mock values
    total = 2 * 1024 * 1024  # 2MB
    used_percent = 25.0
    free = int(total * (1 - used_percent / 100))
    return (total, used_percent, free)


def launch(app_path: str):
    """Launch an app by file path.

    In the emulator, this just stores the app path - actual execution
    is handled by the main emulator loop.
    """
    emulator_state = get_state()
    emulator_state["badger_os_launch"] = app_path

    # Record as running
    app_name = Path(app_path).stem
    state_set_running(app_name)

    if emulator_state.get("trace"):
        print(f"[badger_os] launch({app_path})")


def isfile(path: str) -> bool:
    """Check if path is a file."""
    return os.path.isfile(path)


def isdir(path: str) -> bool:
    """Check if path is a directory."""
    return os.path.isdir(path)


def listdir(path: str = "/"):
    """List directory contents."""
    return os.listdir(path)
