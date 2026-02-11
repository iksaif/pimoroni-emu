"""Main entry point for Pimoroni emulator."""

import argparse
import sys
import os

# Work around macOS Metal renderer crash with pygame/SDL2
# (IOGPUMetalCommandBuffer validate assertion failure)
if sys.platform == "darwin" and "SDL_RENDER_DRIVER" not in os.environ:
    os.environ["SDL_RENDER_DRIVER"] = "opengl"
import runpy
from pathlib import Path
from typing import Optional

from emulator import get_state, _emulator_state
from emulator.devices import get_device, list_devices
from emulator.display import create_display
from emulator.hardware.buttons import ButtonManager
from emulator.hardware.touch import TouchManager
from emulator.hardware.sensors import SensorManager
from emulator.hardware.wifi import WiFiManager
from emulator.mocks import install_mocks, install_inky_mocks, install_badgeware_mocks, setup_vfs


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Pimoroni Device Emulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m emulator --device tufty apps/tufty/badge.py
  python -m emulator --device presto --headless --autosave frames/ apps/presto/app.py
  python -m emulator --device blinky --trace apps/blinky/scroll.py
  python -m emulator --list-devices

Supported devices: tufty, blinky, presto, badger
        """,
    )

    parser.add_argument(
        "app",
        nargs="?",
        help="Path to MicroPython app to run",
    )

    parser.add_argument(
        "-d", "--device",
        default="presto",
        help="Device to emulate (default: presto)",
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without display window (for CI/testing)",
    )

    parser.add_argument(
        "--autosave",
        metavar="DIR",
        help="Auto-save frames to directory on each update()",
    )

    parser.add_argument(
        "--trace",
        action="store_true",
        help="Enable API call tracing",
    )

    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="Exit after N frames (0 = unlimited)",
    )

    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available devices and exit",
    )

    parser.add_argument(
        "--text-output",
        metavar="FILE",
        default=None,
        help="Output frames as ASCII art to FILE (use '-' for stdout)",
    )

    parser.add_argument(
        "--scale",
        type=int,
        default=1,
        help="Display scale factor for window (default: 1)",
    )

    parser.add_argument(
        "--memory-tracking",
        action="store_true",
        help="Enable heap memory tracking (shows usage in UI)",
    )

    parser.add_argument(
        "--strict-memory",
        action="store_true",
        help="Raise MemoryError when emulated heap is exceeded (implies --memory-tracking)",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # List devices and exit
    if args.list_devices:
        print("Available devices:")
        for name in sorted(set(list_devices())):
            device = get_device(name)
            print(f"  {name:12} - {device.description}")
        return 0

    # Require app path
    if not args.app:
        print("Error: App path is required", file=sys.stderr)
        print("Usage: python -m emulator --device <device> <app.py>", file=sys.stderr)
        return 1

    # Check app exists and is a Python file
    app_path = Path(args.app)
    if not app_path.exists():
        print(f"Error: App not found: {app_path}", file=sys.stderr)
        return 1

    if app_path.suffix.lower() != ".py":
        print(f"Error: App must be a Python file (.py), got: {app_path.suffix}", file=sys.stderr)
        print(f"  Did you mean: {app_path.stem}.py?", file=sys.stderr)
        return 1

    # Auto-detect device from app path if using default
    device_name = args.device
    if device_name == "presto":  # Default value - try to auto-detect
        app_path_str = str(app_path).lower()
        if "blinky" in app_path_str:
            device_name = "blinky"
            print(f"Auto-detected device: blinky (from path)")
        elif "tufty" in app_path_str:
            device_name = "tufty"
            print(f"Auto-detected device: tufty (from path)")
        elif "badger" in app_path_str:
            device_name = "badger"
            print(f"Auto-detected device: badger (from path)")
        elif "impression" in app_path_str or "inky_impression" in app_path_str:
            device_name = "inky_impression"
            print(f"Auto-detected device: inky_impression (from path)")
        elif "inky" in app_path_str:
            device_name = "inky_frame"
            print(f"Auto-detected device: inky_frame (from path)")

    # Get device
    try:
        device = get_device(device_name)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Apply display scale override
    if args.scale != 1:
        device.display_scale = args.scale

    print(f"Starting emulator for {device.name}")
    print(f"  Display: {device.display_width}x{device.display_height} {device.display_type}")
    print(f"  App: {app_path}")

    if args.headless:
        print("  Mode: Headless")
    if args.scale != 1:
        print(f"  Scale: {args.scale}x")
    if args.trace:
        print("  Tracing: Enabled")

    # Set up emulator state
    _emulator_state["device"] = device
    _emulator_state["running"] = True
    _emulator_state["headless"] = args.headless
    _emulator_state["trace"] = args.trace
    _emulator_state["max_frames"] = args.max_frames

    # Set up memory tracking (before mocks, so tracemalloc captures app allocations)
    memory_tracking = args.memory_tracking or args.strict_memory
    device_is_rpi = getattr(device, 'is_raspberry_pi', False)
    if memory_tracking and not device_is_rpi and device.heap_size > 0:
        from emulator.memory import MemoryTracker
        tracker = MemoryTracker(
            heap_size=device.heap_size,
            app_path=str(app_path),
            strict=args.strict_memory,
        )
        tracker.start()
        _emulator_state["memory_tracker"] = tracker
        print(f"  Memory: {device.heap_size // 1024}KB heap" +
              (f" + 8MB PSRAM" if device.has_psram else "") +
              (" [strict]" if args.strict_memory else ""))

    # Install mocks based on device type
    library_type = getattr(device, 'library_type', None)
    if library_type == 'inky':
        # Raspberry Pi device using inky library
        install_inky_mocks()
        print("  Library: inky (Raspberry Pi)")
    elif library_type == 'badgeware':
        # Blinky device using badgeware library
        install_badgeware_mocks()
        print("  Library: badgeware (Blinky)")
    else:
        # MicroPython device using picographics
        install_mocks()
        print("  Library: picographics (MicroPython)")

    # Set up virtual filesystem for badger apps
    if "badger" in str(app_path).lower():
        setup_vfs(str(app_path))
        print("  VFS: enabled (badger_os filesystem)")

    # Create display
    display = create_display(device, headless=args.headless)
    _emulator_state["display"] = display

    # Set up autosave
    if args.autosave:
        display.set_autosave(args.autosave)
        print(f"  Autosave: {args.autosave}")

    # Set up text output
    if args.text_output:
        output_file = None if args.text_output == "-" else args.text_output
        display.set_text_output(True, output_file)
        print(f"  Text output: {args.text_output if args.text_output != '-' else 'stdout'}")

    # Initialize display
    display.init()

    # Set up hardware managers
    button_manager = ButtonManager(device)
    touch_manager = TouchManager(device)
    sensor_manager = SensorManager(device)
    wifi_manager = WiFiManager(device)

    # Run the app
    try:
        run_app(app_path, device, display, button_manager, touch_manager,
                sensor_manager, max_frames=args.max_frames)
    except KeyboardInterrupt:
        print("\nInterrupted")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        display.close()
        _emulator_state["running"] = False
        tracker = _emulator_state.get("memory_tracker")
        if tracker:
            tracker.stop()

    print(f"Emulator finished. Rendered {display.get_frame_count()} frames.")
    return 0


def run_app(
    app_path: Path,
    device,
    display,
    button_manager: ButtonManager,
    touch_manager: TouchManager,
    sensor_manager: SensorManager,
    max_frames: int = 0,
):
    """Run the MicroPython app."""
    state = get_state()

    if state["headless"]:
        # Headless mode: just execute the app
        run_app_headless(app_path, max_frames)
    else:
        # Interactive mode with pygame event loop
        run_app_interactive(
            app_path, device, display, button_manager, touch_manager,
            sensor_manager, max_frames
        )


def run_app_headless(app_path: Path, max_frames: int = 0):
    """Run app in headless mode."""
    import threading
    import time

    state = get_state()

    # Run app in separate thread
    def app_thread():
        try:
            # Add app directory to path
            app_dir = str(app_path.parent.absolute())
            if app_dir not in sys.path:
                sys.path.insert(0, app_dir)

            # Run the app
            runpy.run_path(str(app_path), run_name="__main__")
        except Exception as e:
            print(f"App error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            state["running"] = False

    thread = threading.Thread(target=app_thread, daemon=True)
    thread.start()

    # Wait for app to finish or max frames
    while state["running"]:
        time.sleep(0.1)
        if max_frames > 0 and state.get("frame_count", 0) >= max_frames:
            print(f"Reached max frames ({max_frames})")
            state["running"] = False
            break

    thread.join(timeout=1.0)


def _handle_qwstpad_key(state: dict, key_name: str, pressed: bool):
    """Update QwSTPad button bitmask from keyboard input."""
    from emulator.mocks.qwstpad import KEY_TO_BUTTON
    mask = KEY_TO_BUTTON.get(key_name)
    if mask is None or "qwstpad" not in state:
        return
    buttons = state.get("qwstpad_buttons", 0)
    if pressed:
        state["qwstpad_buttons"] = buttons | mask
    else:
        state["qwstpad_buttons"] = buttons & ~mask


def run_app_interactive(
    app_path: Path,
    device,
    display,
    button_manager: ButtonManager,
    touch_manager: TouchManager,
    sensor_manager: SensorManager,
    max_frames: int = 0,
):
    """Run app with interactive pygame window."""
    import pygame
    import threading

    state = get_state()

    # Run app in separate thread
    def app_thread():
        try:
            # Add app directory to path
            app_dir = str(app_path.parent.absolute())
            if app_dir not in sys.path:
                sys.path.insert(0, app_dir)

            # Run the app
            runpy.run_path(str(app_path), run_name="__main__")
        except Exception as e:
            if state["running"]:  # Only print if not intentionally stopped
                print(f"App error: {e}")
                import traceback
                traceback.print_exc()
        finally:
            # E-ink displays retain their image, so keep the window open
            device_obj = state.get("device")
            if not (device_obj and getattr(device_obj, "is_eink", False)):
                state["running"] = False

    thread = threading.Thread(target=app_thread, daemon=True)
    thread.start()

    # Main event loop
    clock = pygame.time.Clock()
    mouse_held_button = None  # Track button held by mouse click

    while state["running"]:
        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                state["running"] = False
                break

            elif event.type == pygame.KEYDOWN:
                key_name = button_manager.pygame_key_to_name(event.key)
                if key_name:
                    if key_name in ("q", "escape"):
                        state["running"] = False
                        break
                    elif key_name == "r":
                        # Reset - would need to restart app
                        print("Reset not implemented yet")
                    else:
                        button_manager.handle_key_down(key_name)
                        _handle_qwstpad_key(state, key_name, pressed=True)

            elif event.type == pygame.KEYUP:
                key_name = button_manager.pygame_key_to_name(event.key)
                if key_name:
                    button_manager.handle_key_up(key_name)
                    _handle_qwstpad_key(state, key_name, pressed=False)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Check if clicking a button indicator
                    btn_key = None
                    if hasattr(display, 'get_button_at'):
                        btn_key = display.get_button_at(*event.pos)
                    if btn_key:
                        mouse_held_button = btn_key
                        button_manager.handle_key_down(btn_key)
                        _handle_qwstpad_key(state, btn_key, pressed=True)
                        if hasattr(display, 'refresh_ui'):
                            display.refresh_ui()
                        continue
                    # Check QwSTPad gamepad widget
                    qwstpad_key = None
                    if hasattr(display, 'get_qwstpad_button_at'):
                        qwstpad_key = display.get_qwstpad_button_at(*event.pos)
                    if qwstpad_key:
                        mouse_held_button = qwstpad_key
                        _handle_qwstpad_key(state, qwstpad_key, pressed=True)
                        if hasattr(display, 'refresh_ui'):
                            display.refresh_ui()
                        continue
                    # Check if display UI wants to handle this
                    if hasattr(display, 'handle_mouse') and display.handle_mouse(*event.pos, True):
                        continue  # Event consumed by UI
                    touch_manager.handle_mouse_down(*event.pos)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    # Release button held by mouse
                    if mouse_held_button:
                        button_manager.handle_key_up(mouse_held_button)
                        _handle_qwstpad_key(state, mouse_held_button, pressed=False)
                        mouse_held_button = None
                        if hasattr(display, 'refresh_ui'):
                            display.refresh_ui()
                        continue
                    # Check if display UI wants to handle this
                    if hasattr(display, 'handle_mouse') and display.handle_mouse(*event.pos, False):
                        continue  # Event consumed by UI
                    touch_manager.handle_mouse_up(*event.pos)

            elif event.type == pygame.MOUSEMOTION:
                if event.buttons[0]:  # Left button held
                    # Check if display UI wants to handle this
                    if hasattr(display, 'handle_mouse') and display.handle_mouse(*event.pos, True):
                        continue  # Event consumed by UI
                    touch_manager.handle_mouse_move(*event.pos)

        # Check max frames
        if max_frames > 0 and state.get("frame_count", 0) >= max_frames:
            print(f"Reached max frames ({max_frames})")
            state["running"] = False
            break

        # Redraw window if the app thread published a new frame
        if hasattr(display, 'tick'):
            display.tick()

        # Limit CPU usage
        clock.tick(60)

    # Wait for app thread to finish
    thread.join(timeout=1.0)


if __name__ == "__main__":
    sys.exit(main())
