# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import signal
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from types import FrameType


@contextmanager
def clean_cli_exit() -> Generator[None]:
    """Context manager for clean keyboard interrupt and signal handling."""

    def signal_handler(signum: int, frame: FrameType | None) -> None:  # noqa: ARG001
        print(f"\n\nReceived signal {signum}.", file=sys.stderr)  # noqa: T201
        sys.exit(128 + signum)

    for sig in [signal.SIGTERM, signal.SIGHUP]:
        signal.signal(sig, signal_handler)

    try:
        yield
    except KeyboardInterrupt:
        print("\n\nInterrupted by user (Ctrl-C).", file=sys.stderr)  # noqa: T201
        sys.exit(130)


def resolve_argv(sys_argv: list[str] | None, fallback: list[str]) -> list[str]:
    """Return the arguments to parse: `None` means fall back to `fallback`,
    while an empty list means no arguments at all."""
    return fallback if sys_argv is None else sys_argv


_duration_report_active = False
_MIN_REPORTED_DURATION = 1.0  # keeps `--help`, `--version` and usage errors free of "Took 0.0s"


def format_duration(seconds: float) -> str:
    """Format a duration for humans, e.g. "4.2s", "2m 05s" or "1h 02m 05s"."""
    if seconds < 59.95:  # below this, rounding to one decimal cannot yield "60.0s"
        return f"{seconds:.1f}s"
    minutes, secs = divmod(round(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    return f"{minutes}m {secs:02d}s"


@contextmanager
def report_duration() -> Generator[None]:
    """Print how long the wrapped command took once it is done (also on failure or interrupt).

    Only the outermost use reports, so a command invoking another command (e.g.
    cmk-dev-install-site calling cmk-dev-site) prints the total time exactly once.
    The report goes to stderr to keep stdout free for machine-readable output, and is
    skipped for runs shorter than a second (e.g. `--help`).
    """
    global _duration_report_active  # pylint: disable=global-statement
    if _duration_report_active:
        yield
        return

    _duration_report_active = True
    start = time.monotonic()
    try:
        yield
    finally:
        _duration_report_active = False
        elapsed = time.monotonic() - start
        if elapsed >= _MIN_REPORTED_DURATION:
            print(f"\nTook {format_duration(elapsed)}", file=sys.stderr)  # noqa: T201
