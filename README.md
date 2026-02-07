# pimoroni-emulator

Desktop emulator for [Pimoroni](https://shop.pimoroni.com/) devices. Run MicroPython and Raspberry Pi apps on your desktop with simulated displays, buttons, and touch input.

## Screenshots

| Tufty 2350 | Presto | Badger 2350 |
|:-:|:-:|:-:|
| ![Tufty 2350](screenshots/tufty.png) | ![Presto](screenshots/presto.png) | ![Badger 2350](screenshots/badger.png) |

| Inky Frame 7.3" | Inky Impression 5.7" |
|:-:|:-:|
| ![Inky Frame](screenshots/inky_frame.png) | ![Inky Impression](screenshots/inky_impression.png) |

## Install

```bash
pip install pimoroni-emulator
```

Or from source:

```bash
git clone --recurse-submodules https://github.com/iksaif/pimoroni-emu
cd pimoroni-emulator
pip install -e ".[dev]"
```

## Usage

```bash
# Run an app on a specific device
pimoroni-emulator --device tufty apps/tufty/hello_badge.py
pimoroni-emulator --device presto apps/presto/touch_demo.py
pimoroni-emulator --device badger apps/badger/hello_badge.py
pimoroni-emulator --device inky_frame apps/inky_frame/hello_inky.py
pimoroni-emulator --device inky_impression apps/inky_impression/hello_impression.py

# Device is auto-detected from app path
pimoroni-emulator apps/tufty/hello_badge.py

# List all supported devices
pimoroni-emulator --list-devices

# Headless mode (for CI/testing)
pimoroni-emulator --device tufty --headless --max-frames 5 app.py

# Save frames to disk
pimoroni-emulator --device presto --autosave frames/ app.py

# Enable API call tracing
pimoroni-emulator --device tufty --trace app.py

# Scale display window
pimoroni-emulator --device tufty --scale 3 app.py
```

### Keyboard controls

- **Q / Escape** - Quit
- **A, S, D, F, G** - Buttons A-E (device-dependent)
- **Up / Down** - UP/DOWN buttons (Tufty, Badger)
- **Mouse click** - Touch input (Presto)

## Compatibility matrix

### Devices

| Family | Device | Display | Resolution | Library | Status |
|--------|--------|---------|------------|---------|--------|
| **Tufty** | Tufty 2350 | TFT IPS | 320x240 | PicoGraphics | Working |
| **Blinky** | Blinky 2350 | LED matrix | 39x26 | Badgeware | Partial |
| **Presto** | Presto | TFT IPS touch | 480x480 | PicoGraphics | Working |
| **Badger** | Badger 2350 | E-ink mono | 296x128 | PicoGraphics | Working |
| **Inky Frame** | 7.3" | E-ink 6-color | 800x480 | PicoGraphics | Working |
| | 5.8" | E-ink 7-color | 600x448 | PicoGraphics | Working |
| | 4.0" | E-ink 7-color | 640x400 | PicoGraphics | Working |
| **Inky Impression** | 7.3" | E-ink 6-color | 800x480 | inky (RPi) | Working |
| | 5.7" | E-ink 7-color | 600x448 | inky (RPi) | Working |
| | 4.0" | E-ink 7-color | 640x400 | inky (RPi) | Working |
| | 13.3" | E-ink 6-color | 1200x1600 | inky (RPi) | Working |

### Mock modules

| Module | Coverage | Notes |
|--------|----------|-------|
| `picographics` | Good | Drawing primitives, text, fonts, framebuffer |
| `pimoroni` | Good | Button class, RGBLED |
| `machine` | Partial | Pin, PWM, I2C, SPI stubs |
| `presto` | Good | Presto class, touch |
| `badger2040` | Good | Badger2040 class |
| `badgeware` | Partial | Drawing API for Blinky |
| `inky` | Good | Inky, InkyImpression, auto-detect |
| `inky_frame` | Good | InkyFrame class |
| `network` / `socket` | Stubs | WiFi connect, basic HTTP |
| `jpegdec` / `pngdec` | Good | Decode via Pillow, render to framebuffer |
| `picovector` | Partial | Basic vector/polygon support |
| Sensors | Stubs | BME280, LTR559, LSM6DS3, QwSTPad |

## Not yet working

### Easy

- **Blinky + PicoGraphics** - Blinky apps using PicoGraphics fail to import `pimoroni`. Fix: register `pimoroni` in `install_badgeware_mocks()` before app thread starts (race condition).
- **E-ink refresh timing** - Display updates instantly. Fix: add optional `time.sleep()` in e-ink `render()`.
- **Audio/buzzer** - Silently ignored. Fix: use `pygame.mixer` to play tones.
- **SD card I/O** - The `SDCard` class maps to a temp dir but `uos.mount()` doesn't wire it up. Fix: translate `/sd/` paths in `_vfs_open()`.

### Medium

- **PicoVector fonts** - Polygons/shapes work, but text falls back to bitmap font. Fix: parse `.af` font files (Alright Fonts, simple binary format) and rasterize glyphs as polygons.
- **Hardware interrupts** - `Pin.irq()` stores handlers but nothing calls `_trigger_irq()` from the button manager. Fix: wire `ButtonManager.handle_key_down()` to `Pin._trigger_irq()`.
- **Real WiFi bridging** - `--real-network` flag exists but doesn't actually connect. Fix: implement using `socket`/`requests` passthrough for `urequests` and `usocket`.
- **Sensor panel interactivity** - Sliders exist for battery but not for light/temperature. Fix: add sensor value sliders to `SensorPanel`.

### Hard

- **Memory constraints** - No simulation of RP2040/RP2350 RAM limits. Would need tracking allocations in mock `gc` module.
- **I2C/SPI peripherals** - Stubs return zeros. Full simulation would require modeling each breakout board's register map.
- **PicoVector SVG** - No SVG file loading. Would need an SVG parser (e.g. via `svgpathtools` or custom).

## Testing

```bash
pytest tests/ -v
```

The test harness supports headless execution, screenshot capture, button simulation, and touch input:

```python
from emulator.testing import DeviceTest

class TestMyApp(DeviceTest):
    device = "tufty"
    app = "apps/tufty/hello_badge.py"

    def test_display(self):
        self.run_frames(5)
        self.screenshot("output.png")

    def test_button(self):
        self.click_button("A")
        self.run_frames(3)
```

## Architecture

```
emulator/
  __main__.py          # CLI entry point
  main.py              # App runner, event loop
  devices/             # Device configs (resolution, buttons, features)
  display/             # Renderers (TFT, LED matrix, e-ink)
  hardware/            # Input simulation (buttons, touch, sensors)
  mocks/               # MicroPython module replacements (~38 modules)
  testing/             # Test harness and screenshot comparison
vendor/                # Upstream submodules (read-only reference)
apps/                  # Demo applications
```

The emulator injects mock modules into `sys.modules` before running your app. Three mock profiles exist:
- **PicoGraphics** - For Tufty, Presto, Badger, Inky Frame
- **Badgeware** - For Blinky 2350
- **inky** - For Inky Impression (Raspberry Pi)

## License

MIT. See [LICENSE](LICENSE).

Vendor submodules under `vendor/` are all MIT-licensed (Pimoroni Ltd).
