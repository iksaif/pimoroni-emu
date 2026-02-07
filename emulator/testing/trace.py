"""API call tracing for debugging."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from emulator import get_state


@dataclass
class TraceEntry:
    """Single trace log entry."""
    timestamp: datetime
    module: str
    function: str
    args: tuple
    kwargs: Dict[str, Any]
    result: Any = None
    error: Optional[str] = None

    def __str__(self):
        args_str = ", ".join(repr(a) for a in self.args)
        kwargs_str = ", ".join(f"{k}={v!r}" for k, v in self.kwargs.items())
        all_args = ", ".join(filter(None, [args_str, kwargs_str]))

        time_str = self.timestamp.strftime("%H:%M:%S.%f")[:-3]
        result_str = f" -> {self.result!r}" if self.result is not None else ""
        error_str = f" ERROR: {self.error}" if self.error else ""

        return f"[{time_str}] {self.module}.{self.function}({all_args}){result_str}{error_str}"


# Global trace log
_trace_log: List[TraceEntry] = []
_tracing_enabled = False


def enable_tracing():
    """Enable API call tracing."""
    global _tracing_enabled
    _tracing_enabled = True
    get_state()["trace"] = True
    print("[trace] Tracing enabled")


def disable_tracing():
    """Disable API call tracing."""
    global _tracing_enabled
    _tracing_enabled = False
    get_state()["trace"] = False
    print("[trace] Tracing disabled")


def is_tracing() -> bool:
    """Check if tracing is enabled."""
    return _tracing_enabled


def log_call(module: str, function: str, args: tuple = (), kwargs: dict = None, result: Any = None):
    """Log an API call.

    Args:
        module: Module name (e.g., "picographics")
        function: Function name (e.g., "rectangle")
        args: Positional arguments
        kwargs: Keyword arguments
        result: Return value
    """
    if not _tracing_enabled:
        return

    entry = TraceEntry(
        timestamp=datetime.now(),
        module=module,
        function=function,
        args=args,
        kwargs=kwargs or {},
        result=result,
    )

    _trace_log.append(entry)

    # Also print to stderr
    print(entry)


def log_error(module: str, function: str, error: str, args: tuple = (), kwargs: dict = None):
    """Log an API call that resulted in an error."""
    if not _tracing_enabled:
        return

    entry = TraceEntry(
        timestamp=datetime.now(),
        module=module,
        function=function,
        args=args,
        kwargs=kwargs or {},
        error=error,
    )

    _trace_log.append(entry)
    print(entry)


def get_trace_log() -> List[TraceEntry]:
    """Get the trace log."""
    return list(_trace_log)


def clear_trace_log():
    """Clear the trace log."""
    global _trace_log
    _trace_log = []


def save_trace_log(filename: str):
    """Save trace log to file."""
    with open(filename, "w") as f:
        for entry in _trace_log:
            f.write(str(entry) + "\n")
    print(f"[trace] Saved {len(_trace_log)} entries to {filename}")


def filter_trace_log(module: Optional[str] = None, function: Optional[str] = None) -> List[TraceEntry]:
    """Filter trace log by module and/or function.

    Args:
        module: Filter by module name (e.g., "picographics")
        function: Filter by function name (e.g., "rectangle")

    Returns:
        Filtered list of trace entries
    """
    result = _trace_log

    if module:
        result = [e for e in result if e.module == module]

    if function:
        result = [e for e in result if e.function == function]

    return result
