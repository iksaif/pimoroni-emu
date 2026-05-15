"""Hardware self-test: push a known frame to the real panel and exit.

Used by ``--hardware-test``. Builds a solid-colour PIL image at the
panel's native resolution and calls ``set_border`` / ``set_image`` /
``show`` directly on the real inky device (bypassing the emulator's
display.render → _push_to_hardware path, which would swallow errors).

Verifies in ~30 seconds (one e-ink refresh) that:
- the real inky library is loaded
- the panel is detected and addressable
- BUSY pin polling works (show() returns rather than hanging forever)

If show() returns in < ~1 second, the panel almost certainly did not
refresh — see README's 'Bookworm: the SPI overlay' section.
"""

import sys
import time

SELF_TEST_COLOUR = (255, 0, 0)  # solid red — unambiguous on every Inky palette
SUSPICIOUSLY_FAST_SHOW_S = 1.0


def run_hardware_self_test(display, device) -> int:
    """Render one solid-colour frame directly to the hardware.

    Returns 0 if every hardware call returned cleanly, 1 otherwise.
    Prints the elapsed wall-time for ``show()`` and flags suspiciously
    fast returns as a likely panel/wiring problem.
    """
    hw = getattr(display, "_hw_device", None)
    if hw is None:
        print(
            "[hardware-test] FAIL: display has no _hw_device — was "
            "--hardware passed and did init_hardware run?",
            file=sys.stderr,
        )
        return 1

    try:
        from PIL import Image
    except ImportError:
        print("[hardware-test] FAIL: PIL is required", file=sys.stderr)
        return 1

    width = device.display_width
    height = device.display_height

    print(
        f"[hardware-test] Pushing solid RGB{SELF_TEST_COLOUR} test frame "
        f"to {width}x{height} panel...",
        flush=True,
    )

    image = Image.new("RGB", (width, height), SELF_TEST_COLOUR)

    try:
        hw.set_border(hw.BLACK)
        hw.set_image(image, saturation=0.5)
        t0 = time.monotonic()
        hw.show()
        show_elapsed = time.monotonic() - t0
    except Exception as e:
        import traceback
        print(f"[hardware-test] FAIL: hardware call raised {e!r}",
              file=sys.stderr)
        traceback.print_exc()
        return 1

    print(f"[hardware-test] show() returned in {show_elapsed:.1f}s",
          flush=True)

    if show_elapsed < SUSPICIOUSLY_FAST_SHOW_S:
        print(
            f"[hardware-test] WARN: show() returned in under "
            f"{SUSPICIOUSLY_FAST_SHOW_S:.0f}s — a real e-ink refresh "
            f"takes many seconds. The panel probably did not actually "
            f"update. See README's 'Bookworm: the SPI overlay' section.",
            file=sys.stderr,
        )
        return 1

    print(
        "[hardware-test] OK — panel should now show solid red.",
        flush=True,
    )
    return 0
