"""Call tracer for real e-ink HAT instances.

Wraps the object returned by ``inky.auto()`` and prints every method
call (name, summarised args, return value, elapsed wall-clock time)
when ``--trace`` is set. Installed automatically under ``--hardware``,
so flipping ``--trace`` is enough to get a full picture of what the
panel sees.

Exceptions are logged unconditionally — those are real errors, not
diagnostics. Attribute access that isn't a callable is forwarded
transparently and silently.
"""

import time
from typing import Any

from emulator import get_state


def _summarise_arg(value: Any) -> str:
    """Render an argument compactly for the trace log."""
    if value is None:
        return "None"
    # PIL.Image.Image — match by duck-type so we don't import PIL here.
    if hasattr(value, "mode") and hasattr(value, "size") and hasattr(value, "save"):
        try:
            w, h = value.size
            return f"<Image {value.mode} {w}x{h}>"
        except Exception:
            return "<Image ?>"
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<{type(value).__name__} len={len(value)}>"
    if isinstance(value, (list, tuple)) and len(value) > 6:
        return f"<{type(value).__name__} len={len(value)}>"
    text = repr(value)
    if len(text) > 80:
        text = text[:77] + "..."
    return text


def _summarise_args(args: tuple, kwargs: dict) -> str:
    parts = [_summarise_arg(a) for a in args]
    parts.extend(f"{k}={_summarise_arg(v)}" for k, v in kwargs.items())
    return ", ".join(parts)


def _summarise_return(value: Any) -> str:
    if value is None:
        return "None"
    if isinstance(value, (int, float, bool, str)):
        text = repr(value)
        return text if len(text) <= 60 else text[:57] + "..."
    return f"<{type(value).__name__}>"


class HardwareTracer:
    """Transparent proxy that logs every method call on the wrapped object.

    Use as ``HardwareTracer(inky.auto(...))`` — downstream code keeps
    calling ``.set_image()`` / ``.show()`` etc. unchanged. Attribute reads
    that aren't callables are forwarded silently; method calls print:

        [Hardware] -> set_image(<Image RGB 800x480>, saturation=0.5)
        [Hardware] <- set_image -> None  (12.3ms)

    A raise also gets logged with the elapsed time before it bubbles up.
    """

    __slots__ = ("_wrapped", "_label")

    def __init__(self, wrapped: Any, label: str = "Hardware"):
        # Bypass our own __setattr__.
        object.__setattr__(self, "_wrapped", wrapped)
        object.__setattr__(self, "_label", label)

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._wrapped, name)
        if not callable(attr) or name.startswith("__"):
            return attr
        label = self._label

        def traced(*args, **kwargs):
            trace_on = bool(get_state().get("trace"))
            if trace_on:
                arg_str = _summarise_args(args, kwargs)
                print(f"[{label}] -> {name}({arg_str})", flush=True)
            t0 = time.monotonic()
            try:
                result = attr(*args, **kwargs)
            except BaseException as exc:
                # Errors always surface — they're not diagnostics.
                elapsed_ms = (time.monotonic() - t0) * 1000
                print(
                    f"[{label}] !! {name} raised "
                    f"{type(exc).__name__}: {exc}  ({elapsed_ms:.1f}ms)",
                    flush=True,
                )
                raise
            if trace_on:
                elapsed_ms = (time.monotonic() - t0) * 1000
                print(
                    f"[{label}] <- {name} -> {_summarise_return(result)}  "
                    f"({elapsed_ms:.1f}ms)",
                    flush=True,
                )
            return result

        traced.__name__ = name
        traced.__qualname__ = f"HardwareTracer.{name}"
        return traced

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._wrapped, name, value)

    def __repr__(self) -> str:
        inner = type(self._wrapped)
        return f"<HardwareTracer wrapping {inner.__module__}.{inner.__name__}>"
