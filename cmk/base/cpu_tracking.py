#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
import os
import time
from typing import Any, Callable, Dict, List, Tuple

from cmk.utils.log import console

# TODO: Move state out of module scope
# TODO: This should be rewritten to a context manager object. See cmk.utils.profile for
#       an example how it could look like.

times: Dict[str, List[float]] = {}
last_time_snapshot: List[float] = []
phase_stack: List[str] = []


def start(initial_phase: str) -> None:
    global times, last_time_snapshot
    console.vverbose("[cpu_tracking] Start with phase '%s'\n" % initial_phase)
    times = {}
    last_time_snapshot = _time_snapshot()

    del phase_stack[:]
    phase_stack.append(initial_phase)


def end() -> None:
    console.vverbose("[cpu_tracking] End\n")
    _add_times_to_phase()
    del phase_stack[:]


def push_phase(phase: str) -> None:
    if _is_not_tracking():
        return

    console.vverbose("[cpu_tracking] Push phase '%s' (Stack: %r)\n" % (phase, phase_stack))
    _add_times_to_phase()
    phase_stack.append(phase)


def pop_phase() -> None:
    if _is_not_tracking():
        return

    console.vverbose("[cpu_tracking] Pop phase '%s' (Stack: %r)\n" % (phase_stack[-1], phase_stack))
    _add_times_to_phase()
    del phase_stack[-1]


def get_times() -> Dict[str, List[float]]:
    return times


def _is_not_tracking() -> bool:
    return not bool(phase_stack)


def _add_times_to_phase() -> None:
    global last_time_snapshot
    new_time_snapshot = _time_snapshot()
    for phase in phase_stack[-1], "TOTAL":
        phase_times = times.get(phase, [0.0] * len(new_time_snapshot))
        times[phase] = [
            phase_times[i] + new_time_snapshot[i] - last_time_snapshot[i]
            for i in range(len(new_time_snapshot))
        ]
    last_time_snapshot = new_time_snapshot


def _time_snapshot() -> List[float]:
    # TODO: Create a better structure for this data
    return list(os.times()[:4]) + [time.time()]


def track(method: Callable) -> Callable:
    """Decorator to track CPU in methods."""
    @functools.wraps(method)
    def wrapper(self: Any, *args: Tuple[Any], **kwargs: Dict[str, Any]) -> None:
        push_phase(self.cpu_tracking_id)
        try:
            return method(self, *args, **kwargs)
        finally:
            pop_phase()

    return wrapper
