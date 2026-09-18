#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import startswith, State

DETECT_ISPRO_SENSORS = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.19011.1.3.2")


def sensors_alarm_states(status: str) -> tuple[State, str]:
    return {
        "1": (State.UNKNOWN, "unknown"),
        "2": (State.WARN, "disable"),
        "3": (State.OK, "normal"),
        "4": (State.WARN, "below low warning"),
        "5": (State.CRIT, "below low critical"),
        "6": (State.WARN, "above high warning"),
        "7": (State.CRIT, "above high critical"),
    }.get(status, (State.UNKNOWN, f"unexpected({status})"))
