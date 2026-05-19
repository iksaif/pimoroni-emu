"""Mock loader for MicroPython modules.

This module injects mock implementations into sys.modules so that
MicroPython imports work in the desktop emulator.
"""

import builtins
import shutil
import sys
from pathlib import Path

# Store original open function
_original_open = builtins.open
_vfs_enabled = False
_vfs_root = None


# Stdlib modules our mocks replace in sys.modules. Real CPython
# libraries (e.g. inky) reach into these at runtime, so it's useful
# debugging info to know they were shadowed. Our mock time/gc currently
# delegate to the real stdlib (mock_time.sleep -> _time.sleep), so in
# practice this is informational, not a smoking gun.
_SHADOWED_STDLIB = {
    "time", "gc", "threading", "socket", "ssl",
    "asyncio", "signal", "select", "selectors", "errno",
}


def _warn_if_shadowing_stdlib(names):
    """Log shadowed stdlib modules under --hardware (informational).

    Lists every stdlib module our mocks are about to overwrite in
    sys.modules. Only fires when --hardware is set — useful context if
    you ever need to debug real-library-meets-mock interactions, but
    not a claim that anything is broken.
    """
    from emulator import get_state
    state = get_state()
    if not state.get("hardware"):
        return
    shadowed = [n for n in names if n in _SHADOWED_STDLIB]
    if not shadowed:
        return
    print(
        f"[mocks] note: shadowing stdlib {shadowed!r} in sys.modules "
        f"(--hardware mode). Our mocks delegate to the real stdlib, so "
        f"this is usually fine — flagged for visibility when debugging.",
        file=sys.stderr,
    )


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

    # Badgeware /system layout — find first match across the upstream
    # vendor submodules and the local apps/ tree. The vendor root is
    # chosen from the active device (Tufty/Badger/Blinky), so e.g.
    # /system/apps/foo on `--device badger` resolves under
    # vendor/badger2350/.
    if path == "/system" or path == "/system/apps" or path == "/rom" \
            or path.startswith("/system/") or path.startswith("/rom/"):
        repo_root = Path(__file__).resolve().parents[2]
        suffix = path.lstrip("/")

        # Pick the vendor root from the device. Order matters: most
        # devices will only have one vendor tree, but we fall back to
        # tufty for backwards compatibility.
        from emulator import get_state as _get_state
        dev = _get_state().get("device")
        dev_name = type(dev).__name__.lower() if dev else ""
        if "badger" in dev_name:
            vendor_roots = [repo_root / "vendor" / "badger2350"]
        elif "blinky" in dev_name:
            vendor_roots = [repo_root / "vendor" / "blinky2350"]
        elif "tufty" in dev_name:
            vendor_roots = [repo_root / "vendor" / "tufty2350"]
        else:
            # Multi-search when no clear device — useful for inspection.
            vendor_roots = [
                repo_root / "vendor" / "tufty2350",
                repo_root / "vendor" / "badger2350",
                repo_root / "vendor" / "blinky2350",
            ]

        candidates = []
        if suffix == "system/apps":
            for v in vendor_roots:
                candidates.append(v / "firmware" / "apps")
        elif suffix == "system":
            for v in vendor_roots:
                candidates.append(v / "firmware")
        elif suffix == "rom":
            for v in vendor_roots:
                candidates.append(v / "romfs")
        elif suffix.startswith("system/apps/"):
            sub = suffix[len("system/apps/"):]
            for v in vendor_roots:
                candidates.append(v / "firmware" / "apps" / sub)
            candidates.append(repo_root / "apps" / sub)
        elif suffix.startswith("system/assets/"):
            sub = suffix[len("system/assets/"):]
            for v in vendor_roots:
                candidates.append(v / "firmware" / "assets" / sub)
        elif suffix.startswith("rom/fonts/"):
            sub = suffix[len("rom/fonts/"):]
            for v in vendor_roots:
                candidates.append(v / "romfs" / "fonts" / sub)
        for c in candidates:
            if c.exists():
                return str(c)

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


def _patch_os_uname():
    """Patch os.uname() to return MicroPython-like values.

    Apps check os.uname().sysname == "rp2" to detect MicroPython on RP2.
    We can't replace the os module, so we monkey-patch uname.
    """
    import os
    from collections import namedtuple
    _uname_result = namedtuple("uname_result",
                               ["sysname", "nodename", "release", "version", "machine"])
    _fake_uname = _uname_result(
        sysname="rp2",
        nodename="rp2",
        release="1.24.1",
        version="MicroPython v1.24.1 (emulator)",
        machine="Raspberry Pi Pico 2 W with RP2350",
    )
    os.uname = lambda: _fake_uname

    # Patch os.mount/os.umount — MicroPython's os has these but CPython doesn't.
    # Apps do `import os; os.mount(sd, "/sd")` which fails without this.
    from emulator.mocks import uos
    if not hasattr(os, "mount"):
        os.mount = uos.mount
    if not hasattr(os, "umount"):
        os.umount = uos.umount
    if not hasattr(os, "sync"):
        os.sync = uos.sync
    if not hasattr(os, "dupterm"):
        os.dupterm = uos.dupterm

    _patch_os_path_translation()


_PATH_TRANSLATED = False


def _patch_os_path_translation():
    """Make os.chdir / os.listdir / os.stat / os.path.exists VFS-aware.

    Apps boot with `os.chdir("/system/apps/foo")` etc. — without this,
    those fall straight through to the host FS and 404. We wrap each
    function so its first argument is run through `_translate_path`.
    """
    global _PATH_TRANSLATED
    if _PATH_TRANSLATED:
        return
    _PATH_TRANSLATED = True

    import os

    def _wrap_first_arg(orig):
        def wrapper(p, *a, **kw):
            return orig(_translate_path(p) if isinstance(p, str) else p, *a, **kw)
        return wrapper

    # Special-cased listdir: /system/apps is a UNION of vendor +
    # local app dirs, so the underlying single path is insufficient.
    _orig_listdir = os.listdir

    def _listdir(p=".", *a, **kw):
        s = str(p) if not isinstance(p, str) else p
        if s in ("/system/apps", "/system/apps/"):
            from emulator import get_state as _gs
            repo_root = Path(__file__).resolve().parents[2]
            dev = _gs().get("device")
            dev_name = type(dev).__name__.lower() if dev else ""
            if "badger" in dev_name:
                vendor = repo_root / "vendor/badger2350/firmware/apps"
            elif "blinky" in dev_name:
                vendor = repo_root / "vendor/blinky2350/firmware/apps"
            else:
                vendor = repo_root / "vendor/tufty2350/firmware/apps"
            entries = set()
            for d in (vendor, repo_root / "apps"):
                if d.is_dir():
                    entries.update(_orig_listdir(str(d)))
            return sorted(entries)
        return _orig_listdir(_translate_path(s) if isinstance(p, str) else p, *a, **kw)

    os.listdir = _listdir

    for attr in ("chdir", "stat", "lstat", "scandir"):
        if hasattr(os, attr):
            setattr(os, attr, _wrap_first_arg(getattr(os, attr)))

    for attr in ("exists", "isdir", "isfile", "islink"):
        if hasattr(os.path, attr):
            setattr(os.path, attr, _wrap_first_arg(getattr(os.path, attr)))

    # Patch os.stat/os.listdir/os.remove/os.rename to translate MicroPython paths
    # (e.g. /sd/img/... -> <app_dir>/img/...) through mount points.
    _original_stat = os.stat
    _original_listdir = os.listdir
    _original_remove = os.remove
    _original_rename = os.rename
    os.stat = lambda path, *args, **kwargs: _original_stat(_translate_path(str(path)), *args, **kwargs)
    os.listdir = lambda path=".", *args, **kwargs: _original_listdir(_translate_path(str(path)), *args, **kwargs)
    os.remove = lambda path, *args, **kwargs: _original_remove(_translate_path(str(path)), *args, **kwargs)
    os.rename = lambda old, new, *args, **kwargs: _original_rename(
        _translate_path(str(old)), _translate_path(str(new)), *args, **kwargs
    )

    # Always patch builtins.open for mount point path translation
    builtins.open = _vfs_open


def install_mocks(device_name=None):
    """Install all mock modules into sys.modules.

    Args:
        device_name: If set, only install mocks relevant to this device.
                     Device-specific modules (presto, tufty2350, etc.) are
                     only installed if they match the device.
    """
    # Import base module (provides trace_log and base classes)
    # Import mocks and register them
    # Hardware sensor mocks
    # Additional breakout sensor mocks
    # WiFi helpers
    from emulator.mocks import (
        badger2040,
        badger_os,
        base,  # noqa: F401
        breakout_as7262,
        breakout_as7343,
        breakout_bh1745,
        breakout_bme68x,
        breakout_bme280,
        breakout_bmp280,
        breakout_dotmatrix,
        breakout_encoder,
        breakout_encoder_wheel,
        breakout_icp10125,
        breakout_ioexpander,
        breakout_ltr559,
        breakout_matrix11x7,
        breakout_mics6814,
        breakout_mlx90640,
        breakout_msa301,
        breakout_pmw3901,
        breakout_potentiometer,
        breakout_rgbmatrix5x5,
        breakout_rtc,
        breakout_scd41,
        breakout_sgp30,
        breakout_trackball,
        breakout_vl53l5cx,
        ezwifi,
        inky_frame,
        jpegdec,
        lsm6ds3,
        machine,
        network,
        network_manager,
        ntptime,
        picographics,
        picovector,
        pimoroni,
        pngdec,
        presto,
        psram,
        qwstpad,
        rp2,
        sdcard,
        touch,
        tufty2350,
        uos,
        urequests,
    )
    from emulator.mocks import gc as mock_gc
    from emulator.mocks import micropython as mock_micropython
    from emulator.mocks import socket as mock_socket
    from emulator.mocks import time as mock_time

    # Warn loudly if --hardware is on; mocking stdlib silently breaks
    # real CPython libraries (e.g. inky.show()'s BUSY-pin sleep loop).
    _warn_if_shadowing_stdlib(["time", "gc"])

    # Core MicroPython modules
    sys.modules["machine"] = machine
    sys.modules["time"] = mock_time
    sys.modules["utime"] = mock_time  # MicroPython alias
    sys.modules["gc"] = mock_gc
    sys.modules["micropython"] = mock_micropython

    # MicroPython asyncio alias (wrapper that auto-creates event loops in threads)
    from emulator.mocks import uasyncio
    sys.modules["uasyncio"] = uasyncio
    sys.modules["rp2"] = rp2

    # MicroPython stdlib aliases
    import json as _json
    sys.modules["ujson"] = _json

    # Patch os.uname() to report as MicroPython on RP2
    _patch_os_uname()

    # Pimoroni libraries
    sys.modules["picographics"] = picographics
    sys.modules["pimoroni"] = pimoroni
    sys.modules["network"] = network
    # Note: Don't replace sys.modules["socket"] - it breaks urllib/SSL
    # Only provide usocket for MicroPython compatibility
    sys.modules["usocket"] = mock_socket
    sys.modules["jpegdec"] = jpegdec

    # Device-specific modules — only install if matching the target device
    # (or if no device specified, install all for backwards compat)
    _dn = (device_name or "").lower()
    if not _dn or "presto" in _dn:
        sys.modules["presto"] = presto
        sys.modules["touch"] = touch
    if not _dn or "tufty" in _dn or "badger" in _dn:
        if "tufty" in _dn or not _dn:
            sys.modules["tufty2350"] = tufty2350
        # Tufty 2350 / Badger 2350 ship with Pimoroni's badgeware
        # firmware (not PicoGraphics). Install the badgeware shim and
        # inject its builtins so apps written against the upstream
        # vendor/<board>/firmware/apps/ trees run unmodified in the
        # emulator. The picographics mock is still installed above for
        # legacy apps in apps/tufty/.
        from emulator.mocks import _msc, badgeware_tufty, easing, wifi
        sys.modules["badgeware"] = badgeware_tufty
        sys.modules["wifi"] = wifi
        sys.modules["_msc"] = _msc
        sys.modules["easing"] = easing
        badgeware_tufty.install_badgeware()
    if not _dn or "inky" in _dn:
        sys.modules["inky_frame"] = inky_frame
    if not _dn or "badger" in _dn:
        sys.modules["badger2040"] = badger2040
        sys.modules["badger_os"] = badger_os
    sys.modules["picovector"] = picovector
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

    Registers all upstream submodules so imports like
    `from inky.inky_uc8159 import Inky` or `from inky.phat import InkyPHAT` work.
    """
    import types

    from emulator.mocks import inky
    from emulator.mocks.inky import auto as inky_auto

    sys.modules["inky"] = inky
    sys.modules["inky.auto"] = inky_auto
    sys.modules["inky.inky"] = inky.inky
    sys.modules["inky.inky_uc8159"] = inky.inky_uc8159
    sys.modules["inky.inky_ac073tc1a"] = inky.inky_ac073tc1a
    sys.modules["inky.inky_spectra6"] = inky.inky_spectra6

    # Alias modules for driver-specific imports that upstream provides
    # (e.g. `from inky.inky_e673 import Inky as InkyE673`)
    # These all map to our existing mock classes.
    _alias_modules = {
        "inky.inky_e673": ("InkyE673", inky.InkyE673),
        "inky.inky_e640": ("InkyE640", inky.InkyE640),
        "inky.inky_el133uf1": ("InkyEL133UF1", inky.InkyEL133UF1),
        "inky.inky_ssd1683": ("InkyWHAT_SSD1683", inky.InkyWHAT_SSD1683),
        "inky.inky_jd79661": ("InkyJD79661", inky.InkyJD79661),
        "inky.inky_jd79668": ("InkyJD79668", inky.InkyJD79668),
    }
    for mod_name, (cls_name, cls) in _alias_modules.items():
        mod = types.ModuleType(mod_name)
        mod.Inky = cls  # upstream convention: each driver exports `Inky`
        setattr(mod, cls_name, cls)
        sys.modules[mod_name] = mod

    # phat/what submodules (upstream uses `from inky.phat import InkyPHAT`)
    phat_mod = types.ModuleType("inky.phat")
    phat_mod.InkyPHAT = inky.InkyPHAT
    phat_mod.InkyPHAT_SSD1608 = inky.InkyPHAT_SSD1608
    sys.modules["inky.phat"] = phat_mod

    what_mod = types.ModuleType("inky.what")
    what_mod.InkyWHAT = inky.InkyWHAT
    sys.modules["inky.what"] = what_mod

    # eeprom module (some apps import it for display variant info)
    eeprom_mod = types.ModuleType("inky.eeprom")
    eeprom_mod.read_eeprom = lambda i2c_bus=None: None
    sys.modules["inky.eeprom"] = eeprom_mod

    # mock module (upstream simulation support)
    mock_mod = types.ModuleType("inky.mock")
    sys.modules["inky.mock"] = mock_mod


def install_badgeware_mocks():
    """Install badgeware mocks for Blinky 2350.

    Badgeware is a custom API used by Blinky that provides drawing primitives,
    shapes, colors, and input handling through builtins.

    Also includes picographics for low-level examples that use both APIs.
    """
    from emulator.mocks import (
        badgeware,
        blinky,
        breakout_bme280,
        easing,
        machine,
        network,
        ntptime,
        picographics,
        picovector,
        pimoroni,
        powman,
        rp2,
        urequests,
    )
    from emulator.mocks import gc as mock_gc
    from emulator.mocks import micropython as mock_micropython
    from emulator.mocks import socket as mock_socket
    from emulator.mocks import time as mock_time

    _warn_if_shadowing_stdlib(["time", "gc"])

    # Core MicroPython modules
    sys.modules["machine"] = machine
    sys.modules["time"] = mock_time
    sys.modules["utime"] = mock_time
    sys.modules["gc"] = mock_gc
    sys.modules["micropython"] = mock_micropython
    sys.modules["network"] = network
    sys.modules["usocket"] = mock_socket

    # MicroPython asyncio alias (wrapper that auto-creates event loops in threads)
    from emulator.mocks import uasyncio
    sys.modules["uasyncio"] = uasyncio
    sys.modules["rp2"] = rp2

    # MicroPython stdlib aliases
    import json as _json
    sys.modules["ujson"] = _json

    # Patch os.uname() to report as MicroPython on RP2
    _patch_os_uname()

    # Blinky-specific modules
    sys.modules["blinky"] = blinky
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

    # Modern badgeware (post-v2.0.1 `badge` API) — install our
    # device-agnostic shim so upstream vendor/blinky2350/firmware/apps/
    # can run unmodified. Legacy `io` is kept as an alias for the older
    # apps in apps/blinky/.
    from emulator.mocks import _msc, badgeware_tufty, wifi
    sys.modules["badgeware"] = badgeware_tufty
    sys.modules["wifi"] = wifi
    sys.modules["_msc"] = _msc
    badgeware_tufty.install_badgeware()

    import builtins as _b
    # Blinky exposes input via `io` (property-based: `BUTTON_A in io.pressed`)
    # rather than `badge` (method-based: `badge.pressed(BUTTON_A)`). The
    # modern badgeware shim has an `_IO` class for exactly this case.
    _b.io = badgeware_tufty.io


def uninstall_mocks():
    """Remove mock modules from sys.modules."""
    mock_names = [
        "machine", "time", "utime", "uasyncio", "rp2", "gc", "micropython",
        "picographics", "pimoroni", "network", "usocket",
        "jpegdec", "presto", "tufty2350", "touch", "inky_frame", "picovector",
        "badger2040", "badger_os", "pngdec", "uos", "ntptime", "sdcard", "urequests",
        # Inky mocks
        "inky", "inky.auto", "inky.inky", "inky.inky_uc8159", "inky.inky_ac073tc1a"
    ]
    teardown_vfs()
    for name in mock_names:
        sys.modules.pop(name, None)
