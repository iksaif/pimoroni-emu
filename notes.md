### LEDs

These four functions do not exist in the real `Presto` class, but are defined in the emulated version: `set_all_leds_rgb`, `set_all_leds_hsv`, `set_led_brightness`, and `update_leds`.

#### Changes:

- Updated the emulator's `Presto` class to remove these functions so the API surface matches the real thing.  
- Removed the unused `_led_brightness` property.
- Modified `get_leds` method so it returns internal `_leds` property without modification.

### Resolution

WIP

