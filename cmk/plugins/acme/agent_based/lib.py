#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

from cmk.agent_based.v2 import startswith, State

DETECT_ACME = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9148")


ACME_ENVIRONMENT_STATES: Final = {
    "1": (State.OK, "initial"),
    "2": (State.OK, "normal"),
    "3": (State.WARN, "minor"),
    "4": (State.WARN, "major"),
    "5": (State.CRIT, "critical"),
    "6": (State.CRIT, "shutdown"),
    "7": (State.CRIT, "not present"),
    "8": (State.CRIT, "not functioning"),
    "9": (State.CRIT, "unknown"),
}
