# CLAUDE.md

## Project overview

Desktop emulator for Pimoroni devices. Runs MicroPython and Raspberry Pi Python apps on desktop by injecting mock modules into `sys.modules`.

## Quick reference

```bash
# Run an app
python -m emulator --device tufty apps/tufty/hello_badge.py

# Run tests
pytest tests/ -v

# Install in dev mode
pip install -e ".[dev]"

# List devices
python -m emulator --list-devices
```

## Repository structure

- `emulator/` - Main package
  - `mocks/` - Mock implementations of MicroPython modules (~38 files)
  - `devices/` - Device configuration dataclasses
  - `display/` - Display renderers (TFT via pygame, LED matrix, e-ink via PIL)
  - `hardware/` - Button, touch, sensor simulation
  - `testing/` - Test harness (DeviceTest base class)
- `vendor/` - **Read-only** git submodules of upstream Pimoroni SDKs
- `apps/` - Demo/test applications
- `tests/` - Pytest test suites

## Keeping mocks in sync with upstream

The `vendor/` directory contains git submodules of the real Pimoroni firmware repos. Our mocks in `emulator/mocks/` must stay compatible with these upstream APIs.

### Workflow for syncing mocks

1. **Update submodules** to latest upstream:
   ```bash
   git submodule update --remote
   ```

2. **Check for API changes** in the upstream MicroPython modules. Key source files:
   - PicoGraphics: `vendor/pimoroni-pico/micropython/modules/picographics/`
   - Presto: `vendor/presto/modules/`
   - Badger: `vendor/badger2040/badger_os/`
   - Blinky/Badgeware: `vendor/blinky2350/modules/`
   - Inky (Python): `vendor/inky/inky/`

3. **Diff the APIs** against our mocks:
   ```bash
   # Example: check what PicoGraphics methods exist upstream
   grep -r "def " vendor/pimoroni-pico/micropython/modules/picographics/ | sort
   # Compare with our mock
   grep -r "def " emulator/mocks/picographics.py | sort
   ```

4. **Update mocks** to match new/changed upstream APIs. The mock should:
   - Accept the same arguments as upstream
   - Return reasonable default values
   - Call into `emulator.display` for any rendering operations
   - Use `trace_log()` from `emulator.mocks.base` for debug tracing

5. **Validate with upstream examples**:
   ```bash
   # Run upstream examples through the emulator
   python -m emulator --device presto vendor/presto/examples/<example>.py
   python -m emulator --device badger vendor/badger2040/examples/<example>.py
   python -m emulator --device tufty vendor/pimoroni-pico/micropython/examples/tufty2350/<example>.py
   ```

### Common sync issues

- **New constants/enums** - PicoGraphics frequently adds display type constants. Check `picographics.py` for `DISPLAY_*` and `PEN_*` values.
- **New drawing methods** - Upstream may add new primitives. Our mock should stub them even if not fully rendered.
- **Import structure changes** - If upstream moves modules around, the mock registration in `emulator/mocks/__init__.py` must match.
- **Blinky dual API** - Blinky apps may use either Badgeware (builtins-based) or PicoGraphics. Both must be installed; see `install_badgeware_mocks()`.

## Validating upstream examples

Not all upstream examples will work because some depend on hardware features we don't emulate (JPEG/PNG decoding, real WiFi, sensors). Test systematically:

```bash
# Quick smoke test: run headless for a few frames
python -m emulator --device <device> --headless --max-frames 5 <example.py>

# Check for import errors (most common failure mode)
python -m emulator --device <device> --headless --max-frames 1 <example.py> 2>&1 | grep -i error

# Batch test all examples for a device
for f in vendor/presto/examples/*.py; do
  echo "=== $f ==="
  timeout 10 python -m emulator --device presto --headless --max-frames 3 "$f" 2>&1 | tail -3
done
```

When an upstream example fails:
1. Check if it's a missing mock module (add stub to `emulator/mocks/` and register in `__init__.py`)
2. Check if it's a missing method on an existing mock (add method stub)
3. Check if it requires real hardware (document as unsupported)

## Adding a new device

1. Create `emulator/devices/<device>.py` with a `BaseDevice` subclass
2. Register it in `emulator/devices/__init__.py`
3. Add any device-specific mock modules in `emulator/mocks/`
4. Register mocks in the appropriate `install_*_mocks()` function
5. Add a demo app in `apps/<device>/`
6. Add device auto-detection in `main.py` (path-based)
7. Update README.md compatibility matrix

## Adding a new mock module

1. Create `emulator/mocks/<module>.py`
2. Implement the public API surface (methods, classes, constants)
3. Register in `emulator/mocks/__init__.py` under the correct `install_*_mocks()` function
4. Use `trace_log("module", "method called")` for tracing support
5. For display-related mocks, call `emulator.get_display()` to access the renderer

## Code conventions

- Python 3.10+, type hints on public APIs
- Dataclasses for device configs
- No upstream code is copied into `emulator/` - mocks reimplement APIs from scratch
- `vendor/` is read-only reference material, never modify it
- Tests use the `DeviceTest` base class from `emulator/testing/`

## Dependencies

- `pygame` - Display rendering, input events (interactive mode)
- `pillow` - Image manipulation (e-ink dithering, screenshots)
- `requests` - HTTP bridging for `--real-network`
- `watchdog` - File watching (future: live reload)
