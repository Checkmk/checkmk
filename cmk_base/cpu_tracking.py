#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import os
import time
from typing import Dict, List  # pylint: disable=unused-import

import cmk_base.console as console

# TODO: Move state out of module scope
# TODO: This should be rewritten to a context manager object. See cmk.utils.profile for
#       an example how it could look like.

times = {}  # type: Dict[str, List[float]]
last_time_snapshot = []  # type: List[float]
phase_stack = []  # type: List[str]


def start(initial_phase):
    # type: (str) -> None
    global times, last_time_snapshot
    console.vverbose("[cpu_tracking] Start with phase '%s'\n" % initial_phase)
    times = {}
    last_time_snapshot = _time_snapshot()

    del phase_stack[:]
    phase_stack.append(initial_phase)


def end():
    # type: () -> None
    console.vverbose("[cpu_tracking] End\n")
    _add_times_to_phase()
    del phase_stack[:]


def push_phase(phase):
    # type: (str) -> None
    if _is_not_tracking():
        return

    console.vverbose("[cpu_tracking] Push phase '%s' (Stack: %r)\n" % (phase, phase_stack))
    _add_times_to_phase()
    phase_stack.append(phase)


def pop_phase():
    # type: () -> None
    if _is_not_tracking():
        return

    console.vverbose("[cpu_tracking] Pop phase '%s' (Stack: %r)\n" % (phase_stack[-1], phase_stack))
    _add_times_to_phase()
    del phase_stack[-1]


def get_times():
    # type: () -> Dict[str, List[float]]
    return times


def _is_not_tracking():
    # type: () -> bool
    return not bool(phase_stack)


def _add_times_to_phase():
    # type: () -> None
    global last_time_snapshot
    new_time_snapshot = _time_snapshot()
    for phase in phase_stack[-1], "TOTAL":
        phase_times = times.get(phase, [0.0] * len(new_time_snapshot))
        times[phase] = [
            phase_times[i] + new_time_snapshot[i] - last_time_snapshot[i]
            for i in range(len(new_time_snapshot))
        ]
    last_time_snapshot = new_time_snapshot


def _time_snapshot():
    # type: () -> List[float]
    # TODO: Create a better structure for this data
    return list(os.times()[:4]) + [time.time()]
