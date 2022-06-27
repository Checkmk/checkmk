#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Mapping, Tuple

from ..agent_based_api.v1 import State

DEVICE_STATES_V4: Mapping[int, Tuple[State, str]] = {
    0: (State.OK, "normal"),
    1: (State.CRIT, "disabled"),
    2: (State.CRIT, "purged"),
    5: (State.WARN, "reading"),
    6: (State.WARN, "settle"),
    7: (State.CRIT, "not found"),
    8: (State.CRIT, "lost"),
    9: (State.CRIT, "read error"),
    10: (State.CRIT, "no comm"),
    11: (State.CRIT, "pwr error"),
    12: (State.CRIT, "breaker tripped"),
    13: (State.CRIT, "fuse blown"),
    14: (State.CRIT, "low alarm"),
    15: (State.WARN, "low warning"),
    16: (State.WARN, "high warning"),
    17: (State.CRIT, "high alarm"),
    18: (State.CRIT, "alarm"),
    19: (State.CRIT, "under limit"),
    20: (State.CRIT, "over limit"),
    21: (State.CRIT, "nvm fail"),
    22: (State.CRIT, "profile error"),
    23: (State.CRIT, "conflict"),
}
