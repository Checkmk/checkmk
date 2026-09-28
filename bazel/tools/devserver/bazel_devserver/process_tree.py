# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Signal and inspect process trees through ``/proc``."""

import contextlib
import os
import signal
import time
from pathlib import Path
from typing import NamedTuple


class Process(NamedTuple):
    """A process, told from a later one of the same PID by its start time."""

    pid: int
    started: int


def signal_group(pgid: int, sig: signal.Signals) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(pgid, sig)


def kill_group_of(process: Process) -> None:
    """Kill the process group of *process*, unless its PID belongs to a later process by now."""
    try:
        pgid = os.getpgid(process.pid)
    except ProcessLookupError, PermissionError:
        return
    if start_time(process.pid) == process.started:
        signal_group(pgid, signal.SIGKILL)


def _stat_fields(pid: int) -> list[str] | None:
    """The fields of ``/proc/<pid>/stat`` after the command name, which may contain anything."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return None
    return stat[stat.rfind(")") + 2 :].split()


def start_time(pid: int) -> int | None:
    """When *pid* started, in clock ticks after boot; tells a process from a later one of the same PID."""
    fields = _stat_fields(pid)
    return int(fields[19]) if fields else None


def has_exited(pid: int) -> bool:
    """Whether *pid* is gone or a zombie that its parent has yet to reap."""
    fields = _stat_fields(pid)
    return fields is None or fields[0] == "Z"


def wait_for_exit(pid: int, timeout: float) -> None:
    """Poll until *pid* exits; ``wait()`` is only available for one's own children."""
    deadline = time.monotonic() + timeout
    while not has_exited(pid) and time.monotonic() < deadline:
        time.sleep(0.1)


def _children(pid: int) -> list[int]:
    children: list[int] = []
    with contextlib.suppress(OSError):
        for task in Path(f"/proc/{pid}/task").iterdir():
            with contextlib.suppress(OSError, ValueError):
                children.extend(int(child) for child in (task / "children").read_text().split())
    return children


def descendants(pid: int) -> list[Process]:
    """All descendants of *pid*, each after its own descendants."""
    result: list[Process] = []
    for child in _children(pid):
        result.extend(descendants(child))
        if (started := start_time(child)) is not None:
            result.append(Process(child, started))
    return result
