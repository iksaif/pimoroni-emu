#!/usr/bin/env python3
"""Test runner for Pimoroni example scripts.

Usage:
    python -m emulator.testing.example_tester vendor/presto/examples/
    python -m emulator.testing.example_tester --device blinky vendor/blinky2350/
"""

import argparse
import subprocess
import sys
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional
import time


@dataclass
class TestResult:
    """Result of testing an example."""
    path: str
    status: str  # "pass", "fail", "error", "timeout", "skip", "unknown"
    frames: int = 0
    duration: float = 0.0
    error: Optional[str] = None
    error_type: Optional[str] = None  # "import", "attribute", "blank", "timeout", "other"
    missing_module: Optional[str] = None
    missing_attr: Optional[str] = None
    output: Optional[str] = None


def categorize_error(stderr: str, stdout: str) -> tuple:
    """Categorize error type and extract details.

    Returns: (error_type, missing_module, missing_attr, error_summary)
    """
    full_output = stderr + stdout

    # Check for missing module
    import_patterns = [
        r"ModuleNotFoundError: No module named '([^']+)'",
        r"ImportError: No module named ([^\s]+)",
        r"No module named '([^']+)'",
    ]
    import re
    for pattern in import_patterns:
        match = re.search(pattern, full_output)
        if match:
            module = match.group(1)
            return ("import", module, None, f"Missing module: {module}")

    # Check for missing attribute/method
    attr_patterns = [
        r"AttributeError: '([^']+)' object has no attribute '([^']+)'",
        r"AttributeError: module '([^']+)' has no attribute '([^']+)'",
        r"has no attribute '([^']+)'",
    ]
    for pattern in attr_patterns:
        match = re.search(pattern, full_output)
        if match:
            if len(match.groups()) == 2:
                obj, attr = match.groups()
                return ("attribute", None, f"{obj}.{attr}", f"Missing: {obj}.{attr}")
            else:
                attr = match.group(1)
                return ("attribute", None, attr, f"Missing attribute: {attr}")

    # Check for NameError
    name_match = re.search(r"NameError: name '([^']+)' is not defined", full_output)
    if name_match:
        name = name_match.group(1)
        return ("name", None, name, f"Undefined name: {name}")

    # Check for file not found
    file_match = re.search(r"FileNotFoundError:.*'([^']+)'", full_output)
    if file_match:
        return ("file", None, None, f"File not found")

    # Check for TypeError (often means wrong API usage)
    type_match = re.search(r"TypeError: ([^\n]+)", full_output)
    if type_match:
        return ("type", None, None, f"TypeError: {type_match.group(1)[:50]}")

    # Check for syntax errors
    if "SyntaxError" in full_output:
        return ("syntax", None, None, "Syntax error")

    # Generic error - extract last exception line
    lines = full_output.strip().split("\n")
    for line in reversed(lines):
        if line.strip() and not line.startswith(" "):
            if "Error" in line or "Exception" in line:
                return ("other", None, None, line.strip()[:80])

    return ("other", None, None, None)


@dataclass
class TestReport:
    """Report of all tests run."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    timeouts: int = 0
    skipped: int = 0
    unknown: int = 0
    results: List[TestResult] = field(default_factory=list)


def find_examples(path: Path, pattern: str = "*.py") -> List[Path]:
    """Find all Python example files."""
    examples = []

    if path.is_file():
        if path.suffix == ".py":
            examples.append(path)
    else:
        # Recursively find all .py files
        for py_file in path.rglob(pattern):
            # Skip __init__.py, __pycache__, setup.py, etc.
            name = py_file.name
            if name.startswith("__") or name.startswith("."):
                continue
            if name in ("setup.py", "conftest.py", "secrets.py"):
                continue
            if "__pycache__" in str(py_file):
                continue
            examples.append(py_file)

    return sorted(examples)


def test_example(
    example: Path,
    device: Optional[str] = None,
    timeout: int = 10,
    max_frames: int = 5,
) -> TestResult:
    """Test a single example script."""
    result = TestResult(path=str(example), status="unknown")

    # Build command
    cmd = [
        sys.executable, "-m", "emulator",
        "--headless",
        "--max-frames", str(max_frames),
    ]

    if device:
        cmd.extend(["--device", device])

    cmd.append(str(example))

    start = time.time()

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent.parent.parent,  # Project root
        )

        result.duration = time.time() - start
        result.output = proc.stdout + proc.stderr

        # Parse frame count from output
        for line in result.output.split("\n"):
            if "Rendered" in line and "frames" in line:
                try:
                    # "Emulator finished. Rendered N frames."
                    parts = line.split()
                    idx = parts.index("Rendered")
                    result.frames = int(parts[idx + 1])
                except (ValueError, IndexError):
                    pass

        # Check for errors in output even if return code is 0
        # (emulator returns 0 even if app crashes)
        error_type, missing_mod, missing_attr, error_summary = categorize_error(
            proc.stderr, proc.stdout
        )

        if error_type and error_type not in ("other",):
            # Found a specific error in output
            result.status = "error"
            result.error_type = error_type
            result.missing_module = missing_mod
            result.missing_attr = missing_attr
            result.error = error_summary
        elif proc.returncode == 0:
            if result.frames > 0:
                result.status = "pass"
            else:
                # No frames could mean waiting for input, or blank screen - mark as unknown
                result.status = "unknown"
                result.error = "No frames rendered (may be waiting for input)"
                result.error_type = "blank"
        else:
            result.status = "error"
            # Categorize the error
            error_type, missing_mod, missing_attr, error_summary = categorize_error(
                proc.stderr, proc.stdout
            )
            result.error_type = error_type
            result.missing_module = missing_mod
            result.missing_attr = missing_attr

            if error_summary:
                result.error = error_summary
            else:
                # Fall back to last few lines of stderr
                stderr = proc.stderr.strip()
                if stderr:
                    lines = stderr.split("\n")
                    result.error = "\n".join(lines[-3:])
                else:
                    result.error = f"Exit code {proc.returncode}"

    except subprocess.TimeoutExpired:
        result.duration = timeout
        result.status = "timeout"
        result.error = f"Timed out after {timeout}s"
        result.error_type = "timeout"

    except Exception as e:
        result.duration = time.time() - start
        result.status = "error"
        result.error = str(e)

    return result


def run_tests(
    paths: List[Path],
    device: Optional[str] = None,
    timeout: int = 10,
    max_frames: int = 5,
    verbose: bool = False,
) -> TestReport:
    """Run tests on all examples."""
    report = TestReport()

    # Find all examples
    examples = []
    for path in paths:
        examples.extend(find_examples(Path(path)))

    report.total = len(examples)
    print(f"Found {report.total} examples to test\n")

    for i, example in enumerate(examples, 1):
        # Progress indicator
        rel_path = example.name
        print(f"[{i}/{report.total}] Testing {rel_path}...", end=" ", flush=True)

        result = test_example(
            example,
            device=device,
            timeout=timeout,
            max_frames=max_frames,
        )

        report.results.append(result)

        # Update counts
        if result.status == "pass":
            report.passed += 1
            print(f"\033[32mPASS\033[0m ({result.frames} frames, {result.duration:.1f}s)")
        elif result.status == "timeout":
            report.timeouts += 1
            print(f"\033[33mTIMEOUT\033[0m")
        elif result.status == "skip":
            report.skipped += 1
            print(f"\033[36mSKIP\033[0m")
        elif result.status == "unknown":
            report.unknown += 1
            print(f"\033[33mUNKNOWN\033[0m (no frames)")
        elif result.status == "fail":
            report.failed += 1
            print(f"\033[31mFAIL\033[0m")
        else:
            report.errors += 1
            print(f"\033[31mERROR\033[0m")

        if verbose and result.error:
            print(f"    Error: {result.error[:200]}")

    return report


def print_summary(report: TestReport):
    """Print test summary."""
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total:    {report.total}")
    print(f"Passed:   \033[32m{report.passed}\033[0m")
    print(f"Failed:   \033[31m{report.failed}\033[0m")
    print(f"Errors:   \033[31m{report.errors}\033[0m")
    print(f"Timeouts: \033[33m{report.timeouts}\033[0m")
    print(f"Unknown:  \033[33m{report.unknown}\033[0m")
    print(f"Skipped:  \033[36m{report.skipped}\033[0m")

    # Group issues by type
    error_types = {}
    for r in report.results:
        if r.status in ("fail", "error", "timeout", "unknown"):
            etype = r.error_type or "other"
            if etype not in error_types:
                error_types[etype] = []
            error_types[etype].append(r)

    # Print by category
    if error_types:
        print("\n" + "-" * 60)
        print("ISSUES BY CATEGORY:")

        # Missing modules
        if "import" in error_types:
            print("\n\033[33mMissing Modules:\033[0m")
            modules = {}
            for r in error_types["import"]:
                mod = r.missing_module or "unknown"
                if mod not in modules:
                    modules[mod] = []
                modules[mod].append(r.path)
            for mod, paths in sorted(modules.items()):
                print(f"  {mod}: {len(paths)} examples")
                for p in paths[:3]:
                    print(f"    - {Path(p).name}")
                if len(paths) > 3:
                    print(f"    ... and {len(paths) - 3} more")

        # Missing attributes/methods
        if "attribute" in error_types:
            print("\n\033[33mMissing Attributes/Methods:\033[0m")
            attrs = {}
            for r in error_types["attribute"]:
                attr = r.missing_attr or r.error
                if attr not in attrs:
                    attrs[attr] = []
                attrs[attr].append(r.path)
            for attr, paths in sorted(attrs.items()):
                print(f"  {attr}: {len(paths)} examples")
                for p in paths[:2]:
                    print(f"    - {Path(p).name}")

        # Blank screens / unknown
        if "blank" in error_types:
            print("\n\033[33mNo Frames (waiting for input?):\033[0m")
            for r in error_types["blank"]:
                print(f"  - {Path(r.path).name}")

        # Timeouts
        if "timeout" in error_types:
            print("\n\033[33mTimeouts (infinite loop?):\033[0m")
            for r in error_types["timeout"]:
                print(f"  - {Path(r.path).name}")

        # Other errors
        other_types = set(error_types.keys()) - {"import", "attribute", "blank", "timeout"}
        if other_types:
            print("\n\033[33mOther Errors:\033[0m")
            for etype in sorted(other_types):
                for r in error_types[etype]:
                    print(f"  [{etype}] {Path(r.path).name}: {r.error[:60] if r.error else ''}")


def main():
    parser = argparse.ArgumentParser(description="Test Pimoroni examples")
    parser.add_argument("paths", nargs="+", help="Paths to example files or directories")
    parser.add_argument("-d", "--device", help="Device to emulate")
    parser.add_argument("-t", "--timeout", type=int, default=10, help="Timeout per test (seconds)")
    parser.add_argument("-f", "--max-frames", type=int, default=5, help="Max frames per test")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show error details")
    parser.add_argument("--json", metavar="FILE", help="Write JSON report to file")

    args = parser.parse_args()

    report = run_tests(
        [Path(p) for p in args.paths],
        device=args.device,
        timeout=args.timeout,
        max_frames=args.max_frames,
        verbose=args.verbose,
    )

    print_summary(report)

    # Write JSON report
    if args.json:
        with open(args.json, "w") as f:
            json.dump({
                "summary": {
                    "total": report.total,
                    "passed": report.passed,
                    "failed": report.failed,
                    "errors": report.errors,
                    "timeouts": report.timeouts,
                    "skipped": report.skipped,
                },
                "results": [asdict(r) for r in report.results],
            }, f, indent=2)
        print(f"\nJSON report written to: {args.json}")

    # Exit with appropriate code
    if report.failed > 0 or report.errors > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
