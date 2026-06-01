I had some problems running a couple of the demo apps on both the emulator and a real Presto. There were two different issues: (1) the demo apps use some APIs to control the LEDs that aren't there in the hardware SDK, and (2) the hardware SDK supports full and half resolution that the emulator doesn't handle.

This PR fixes both of these things by updating the emulator mocks and updates the demo apps where necessary. Now the demo apps work correctly on both the real hardware and the emulator.

### 1. LEDs

These four functions do not exist in the real `Presto` class, but are defined in the emulated version: `set_all_leds_rgb`, `set_all_leds_hsv`, `set_led_brightness`, and `update_leds`.

#### Changes:

- Updated the emulator's `Presto` class to remove these functions so the API surface matches the real thing.
- Removed the unused `_led_brightness` property.
- Modified `get_leds` method so it returns internal `_leds` property without modification.

### 2. Screen Resolution

When running the demo Presto application in the emulator, `apps/presto/touch_demo.py`, mouse clicks on the emulated touchscreen map incorrectly. The touch indicator appears shifted toward the top-left of the screen relative to where the cursor clicked.

I dug into this, and the problem is that the real Presto SDK defaults to half-resolution mode (`full_res=False`), setting a graphics canvas size of `240x240` pixels, which the hardware displays scaled to the physical `480x480` screen. The emulator didn't respect these two modes, so when you construct a `Presto` instance with the defaults, it is `240x240` on real hardware and `480x480` on the emulator.

Whenever an app asks the Presto object what the resolution is, it hardcoded a response of 480x480, but the real hardware would return 240x240 _or_ 480x480, depending on how it was constructed.

#### Changes:

- Added `DISPLAY_PRESTO_FULL_RES` to `picographics.py` and mapped it to `(480, 480)`.
- Updated `DISPLAY_PRESTO` in `picographics.py` to map to its actual SDK-standard half-resolution size of `(240, 240)`.
- Updated the `Presto` constructor in `presto.py` to initialize `PicoGraphics` with `DISPLAY_PRESTO_FULL_RES` when `full_res=True`, and `DISPLAY_PRESTO` otherwise.
- Updated the `TFTDisplay.render` method in `tft.py` to dynamically resize the underlying Pygame surface when the dimensions of the incoming framebuffer change. This ensures that the half-resolution `240x240` buffer is upscaled cleanly to the `480x480` physical emulator window using nearest-neighbor scaling.
- Updated the two demo apps `touch_demo.py` and `vector_text_demo.py` to use `Presto(full_res=True)`. Since both applications use hardcoded coordinates outside the 240x240 boundary, they require the full resolution canvas to draw their layout correctly without clipping.

I also added a couple tests (with LLM assistance) to exercise this code.
