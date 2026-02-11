"""Mock loader for MicroPython modules.

This module injects mock implementations into sys.modules so that
MicroPython imports work in the desktop emulator.
"""

import sys
import builtins
import shutil
from pathlib import Path


# Store original open function
_original_open = builtins.open
_vfs_enabled = False
_vfs_root = None


def _translate_path(path: str) -> str:
    """Translate MicroPython absolute path to host filesystem path.

    Checks uos mount points first (e.g. /sd/), then translates known
    MicroPython device paths like /badges/, /examples/, etc.
    """
    if not isinstance(path, str):
        return path

    # Check uos mount points (works even without VFS enabled)
    if path.startswith("/"):
        try:
            from emulator.mocks import uos
            mount_points = getattr(uos, '_mount_points', {})
            for mount_path, local_path in sorted(mount_points.items(), key=lambda x: -len(x[0])):
                if path == mount_path or path.startswith(mount_path + "/"):
                    remainder = path[len(mount_path):].lstrip("/")
                    return str(Path(local_path) / remainder)
        except ImportError:
            pass

    global _vfs_root
    if not _vfs_enabled or not _vfs_root:
        return path

    # Only translate known MicroPython filesystem paths
    micropython_roots = ("/badges", "/examples", "/icons", "/images", "/books")
    if path.startswith(micropython_roots):
        return str(Path(_vfs_root) / path.lstrip("/"))

    return path


def _vfs_open(path, mode="r", *args, **kwargs):
    """Open function with VFS path translation."""
    translated = _translate_path(path)
    return _original_open(translated, mode, *args, **kwargs)


def setup_vfs(app_path: str, vfs_root: str = "/tmp/badger_vfs"):
    """Set up virtual filesystem for an app.

    This copies necessary files from the app's directory structure
    to a temporary VFS location that mimics the MicroPython filesystem.

    Args:
        app_path: Path to the app file being run
        vfs_root: Root directory for the virtual filesystem
    """
    global _vfs_enabled, _vfs_root

    _vfs_root = vfs_root
    vfs_path = Path(vfs_root)

    # Find the app's base directory (e.g., badger_os folder)
    app_file = Path(app_path).resolve()
    app_dir = app_file.parent

    # Look for common badger_os structure
    if "badger_os" in str(app_dir) or "examples" in str(app_dir):
        # Find the badger_os root
        current = app_dir
        while current.parent != current:
            if (current / "badges").exists() or (current / "examples").exists():
                break
            current = current.parent

        # Copy directory structure to VFS
        for subdir in ["badges", "examples", "icons", "images", "books"]:
            src = current / subdir
            if src.exists():
                dst = vfs_path / subdir
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)

    # Enable VFS and patch open
    _vfs_enabled = True
    builtins.open = _vfs_open

    # Store in emulator state for uos module
    from emulator import get_state
    state = get_state()
    state["vfs_root"] = vfs_root


def teardown_vfs():
    """Restore original open function and disable VFS."""
    global _vfs_enabled
    _vfs_enabled = False
    builtins.open = _original_open


def install_mocks():
    """Install all mock modules into sys.modules."""
    # Import base module (provides trace_log and base classes)
    from emulator.mocks import base  # noqa: F401

    # Import mocks and register them
    from emulator.mocks import machine
    from emulator.mocks import time as mock_time
    from emulator.mocks import gc as mock_gc
    from emulator.mocks import micropython as mock_micropython
    from emulator.mocks import picographics
    from emulator.mocks import pimoroni
    from emulator.mocks import network
    from emulator.mocks import socket as mock_socket
    from emulator.mocks import jpegdec
    from emulator.mocks import presto
    from emulator.mocks import tufty2350
    from emulator.mocks import touch
    from emulator.mocks import inky_frame
    from emulator.mocks import picovector
    from emulator.mocks import badger2040
    from emulator.mocks import badger_os
    from emulator.mocks import pngdec
    from emulator.mocks import uos
    from emulator.mocks import ntptime
    from emulator.mocks import sdcard
    from emulator.mocks import urequests
    # Hardware sensor mocks
    from emulator.mocks import breakout_bme280
    from emulator.mocks import breakout_ltr559
    from emulator.mocks import lsm6ds3
    from emulator.mocks import qwstpad
    from emulator.mocks import psram
    # Additional breakout sensor mocks
    from emulator.mocks import breakout_bme68x
    from emulator.mocks import breakout_bmp280
    from emulator.mocks import breakout_scd41
    from emulator.mocks import breakout_sgp30
    from emulator.mocks import breakout_rtc
    from emulator.mocks import breakout_potentiometer
    from emulator.mocks import breakout_encoder
    from emulator.mocks import breakout_trackball
    from emulator.mocks import breakout_msa301
    from emulator.mocks import breakout_bh1745
    from emulator.mocks import breakout_as7262
    from emulator.mocks import breakout_as7343
    from emulator.mocks import breakout_dotmatrix
    from emulator.mocks import breakout_rgbmatrix5x5
    from emulator.mocks import breakout_matrix11x7
    from emulator.mocks import breakout_ioexpander
    from emulator.mocks import breakout_encoder_wheel
    from emulator.mocks import breakout_icp10125
    from emulator.mocks import breakout_mics6814
    from emulator.mocks import breakout_vl53l5cx
    from emulator.mocks import breakout_pmw3901
    from emulator.mocks import breakout_mlx90640
    # WiFi helpers
    from emulator.mocks import ezwifi
    from emulator.mocks import network_manager

    # Core MicroPython modules
    sys.modules["machine"] = machine
    sys.modules["time"] = mock_time
    sys.modules["utime"] = mock_time  # MicroPython alias
    sys.modules["gc"] = mock_gc
    sys.modules["micropython"] = mock_micropython

    # Pimoroni libraries
    sys.modules["picographics"] = picographics
    sys.modules["pimoroni"] = pimoroni
    sys.modules["network"] = network
    # Note: Don't replace sys.modules["socket"] - it breaks urllib/SSL
    # Only provide usocket for MicroPython compatibility
    sys.modules["usocket"] = mock_socket
    sys.modules["jpegdec"] = jpegdec

    # Device-specific modules
    sys.modules["presto"] = presto
    sys.modules["tufty2350"] = tufty2350
    sys.modules["touch"] = touch
    sys.modules["inky_frame"] = inky_frame
    sys.modules["picovector"] = picovector
    sys.modules["badger2040"] = badger2040
    sys.modules["badger_os"] = badger_os
    sys.modules["pngdec"] = pngdec
    sys.modules["uos"] = uos
    sys.modules["ntptime"] = ntptime
    sys.modules["sdcard"] = sdcard
    sys.modules["urequests"] = urequests
    # Hardware sensor mocks
    sys.modules["breakout_bme280"] = breakout_bme280
    sys.modules["breakout_ltr559"] = breakout_ltr559
    sys.modules["lsm6ds3"] = lsm6ds3
    sys.modules["qwstpad"] = qwstpad
    sys.modules["psram"] = psram
    # Additional breakout sensor mocks
    sys.modules["breakout_bme68x"] = breakout_bme68x
    sys.modules["breakout_bmp280"] = breakout_bmp280
    sys.modules["breakout_scd41"] = breakout_scd41
    sys.modules["breakout_sgp30"] = breakout_sgp30
    sys.modules["breakout_rtc"] = breakout_rtc
    sys.modules["breakout_potentiometer"] = breakout_potentiometer
    sys.modules["breakout_encoder"] = breakout_encoder
    sys.modules["breakout_trackball"] = breakout_trackball
    sys.modules["breakout_msa301"] = breakout_msa301
    sys.modules["breakout_bh1745"] = breakout_bh1745
    sys.modules["breakout_as7262"] = breakout_as7262
    sys.modules["breakout_as7343"] = breakout_as7343
    sys.modules["breakout_dotmatrix"] = breakout_dotmatrix
    sys.modules["breakout_rgbmatrix5x5"] = breakout_rgbmatrix5x5
    sys.modules["breakout_matrix11x7"] = breakout_matrix11x7
    sys.modules["breakout_ioexpander"] = breakout_ioexpander
    sys.modules["breakout_encoder_wheel"] = breakout_encoder_wheel
    sys.modules["breakout_icp10125"] = breakout_icp10125
    sys.modules["breakout_mics6814"] = breakout_mics6814
    sys.modules["breakout_vl53l5cx"] = breakout_vl53l5cx
    sys.modules["breakout_pmw3901"] = breakout_pmw3901
    sys.modules["breakout_mlx90640"] = breakout_mlx90640
    # WiFi helpers
    sys.modules["ezwifi"] = ezwifi
    sys.modules["network_manager"] = network_manager
    # Note: Don't replace sys.modules["os"] - it breaks CPython internals

    # Initialize battery mock
    from emulator.mocks.battery import init_battery
    init_battery()


def install_inky_mocks():
    """Install Inky library mocks for Raspberry Pi devices.

    This is separate from MicroPython mocks since Inky uses regular Python
    and runs on Raspberry Pi (not RP2040/RP2350).
    """
    from emulator.mocks import inky
    from emulator.mocks.inky import auto as inky_auto

    sys.modules["inky"] = inky
    sys.modules["inky.auto"] = inky_auto
    sys.modules["inky.inky"] = inky.inky
    sys.modules["inky.inky_uc8159"] = inky.inky_uc8159
    sys.modules["inky.inky_ac073tc1a"] = inky.inky_ac073tc1a


def install_badgeware_mocks():
    """Install badgeware mocks for Blinky 2350.

    Badgeware is a custom API used by Blinky that provides drawing primitives,
    shapes, colors, and input handling through builtins.

    Also includes picographics for low-level examples that use both APIs.
    """
    from emulator.mocks import machine
    from emulator.mocks import time as mock_time
    from emulator.mocks import gc as mock_gc
    from emulator.mocks import micropython as mock_micropython
    from emulator.mocks import network
    from emulator.mocks import socket as mock_socket
    from emulator.mocks import blinky
    from emulator.mocks import badgeware
    from emulator.mocks import picovector
    from emulator.mocks import picographics
    from emulator.mocks import ntptime
    from emulator.mocks import powman
    from emulator.mocks import pimoroni
    from emulator.mocks import breakout_bme280
    from emulator.mocks import easing
    from emulator.mocks import urequests

    # Core MicroPython modules
    sys.modules["machine"] = machine
    sys.modules["time"] = mock_time
    sys.modules["utime"] = mock_time
    sys.modules["gc"] = mock_gc
    sys.modules["micropython"] = mock_micropython
    sys.modules["network"] = network
    sys.modules["usocket"] = mock_socket

    # Blinky-specific modules
    sys.modules["blinky"] = blinky
    sys.modules["badgeware"] = badgeware
    sys.modules["picovector"] = picovector
    sys.modules["picographics"] = picographics
    sys.modules["ntptime"] = ntptime
    sys.modules["powman"] = powman
    sys.modules["pimoroni"] = pimoroni
    sys.modules["breakout_bme280"] = breakout_bme280
    sys.modules["easing"] = easing
    sys.modules["urequests"] = urequests

    # Initialize battery mock
    from emulator.mocks.battery import init_battery
    init_battery()

    # Initialize blinky display
    blinky_display = blinky.Blinky()

    # Create screen and install builtins
    badgeware._create_screen()
    badgeware._setup_builtins()

    # Link the badgeware screen buffer to the blinky display buffer
    badgeware.screen._buffer = blinky_display._buffer


def uninstall_mocks():
    """Remove mock modules from sys.modules."""
    mock_names = [
        "machine", "time", "utime", "gc", "micropython",
        "picographics", "pimoroni", "network", "usocket",
        "jpegdec", "presto", "tufty2350", "touch", "inky_frame", "picovector",
        "badger2040", "badger_os", "pngdec", "uos", "ntptime", "sdcard", "urequests",
        # Inky mocks
        "inky", "inky.auto", "inky.inky", "inky.inky_uc8159", "inky.inky_ac073tc1a"
    ]
    teardown_vfs()
    for name in mock_names:
        sys.modules.pop(name, None)
