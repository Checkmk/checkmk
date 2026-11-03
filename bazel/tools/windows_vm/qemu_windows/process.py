# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Process setup for the programs that run a QEMU: the image build, the
state action, core-vm and the tier runner."""

import io
import signal
import sys
from types import FrameType


def setup() -> None:
    """Line-buffered stdout, so that each line comes before the output that
    follows it, and SIGTERM and SIGHUP raise SystemExit like Ctrl-C: the QEMU
    quits and the cleanup runs on the way out (a SIGKILL instead takes QEMU
    down through its parent-death signal)."""
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(line_buffering=True)
    for signum in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, _exit_on_signal)


def _exit_on_signal(signum: int, _frame: FrameType | None) -> None:
    raise SystemExit(128 + signum)
