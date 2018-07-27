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

import cmk_base.console as console

try:
    _
except NameError:
    _ = lambda x: x # Fake i18n when not available

# TODO: Move state out of module scope
# TODO: This should be rewritten to a context manager object. See cmk.profile for
#       an example how it could look like.

current_phase = None

def start(initial_phase):
    global times, last_time_snapshot, current_phase, phase_stack
    times = {}
    console.vverbose("[cpu_tracking] Start with phase '%s'\n" % initial_phase)
    last_time_snapshot = _time_snapshot()
    current_phase = initial_phase
    phase_stack = []
    _set_phase(initial_phase)


def end():
    console.vverbose("[cpu_tracking] End\n")
    _set_phase(None)


def push_phase(phase):
    if current_phase != None:
        console.vverbose("[cpu_tracking] Push phase (Stack: %r)\n" % phase_stack)
        phase_stack.append(current_phase)
        _set_phase(phase)


def pop_phase():
    if current_phase != None:
        console.vverbose("[cpu_tracking] Pop current phase (Stack: %r)\n" % phase_stack)
        if len(phase_stack) == 1:
            _set_phase(None)
        else:
            _set_phase(phase_stack[-1])

        del phase_stack[-1]


def get_times():
    return times


def _set_phase(phase):
    global current_phase
    if current_phase != None:
        console.vverbose("[cpu_tracking]   Set phase: %s (previous %s)\n" % (phase, current_phase))
        _add_times_to_phase()
        current_phase = phase


def _add_times_to_phase():
    global last_time_snapshot
    new_time_snapshot = _time_snapshot()
    for phase in current_phase, "TOTAL":
        phase_times = times.get(phase, [ 0.0 ] * len(new_time_snapshot))
        times[phase] = [
            phase_times[i] + new_time_snapshot[i] - last_time_snapshot[i]
            for i in range(len(new_time_snapshot)) ]
    last_time_snapshot = new_time_snapshot


def _time_snapshot():
    return list(os.times()[:4]) + [ time.time() ]
