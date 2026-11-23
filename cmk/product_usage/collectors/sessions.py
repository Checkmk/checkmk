#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import statistics
from pathlib import Path

from cmk.ccc import store
from cmk.product_usage.schedule import CLOUD_TRIAL_INTERVAL
from cmk.product_usage.schema import SessionStats


def collect(var_dir: Path, *, now: int) -> SessionStats:
    """Statistics of the sessions of all users that started in the trial interval before now"""
    # The window is as long as the interval between trial runs, so the windows of scheduled runs
    # do not overlap
    window_start = now - CLOUD_TRIAL_INTERVAL.total_seconds()
    durations = [
        last_activity - started_at
        for path in (var_dir / "web").glob("*/session_info.mk")
        for started_at, last_activity in _read_sessions(path)
        if started_at > window_start
    ]
    if not durations:
        return SessionStats(
            count=0, average_duration=None, median_duration=None, stddev_duration=None
        )
    return SessionStats(
        count=len(durations),
        average_duration=statistics.fmean(durations),
        median_duration=statistics.median(durations),
        stddev_duration=statistics.pstdev(durations),
    )


def _read_sessions(path: Path) -> list[tuple[int, int]]:
    # Locking creates the file empty before the GUI writes the user's first session to it
    if not (text := store.load_text_from_file(path)):
        return []
    return [
        (session_info["started_at"], session_info["last_activity"])
        for session_info in ast.literal_eval(text).values()
    ]
