#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Define domain models.

We explicitly want to separate these models from those that are defined in third-party clients like
the REST API. The goal is to prevent leakage from the validation layer into our internal business
logic.
"""

import dataclasses
import datetime as dt
import enum
from typing import assert_never, Literal

type ServiceStateLabel = Literal["OK", "WARN", "CRIT", "UNKN"]


class ServiceState(enum.IntEnum):
    OK = 0
    WARN = 1
    CRIT = 2
    UNKN = 3


@dataclasses.dataclass(frozen=True)
class Service:
    name: str
    state: ServiceState
    summary: str
    last_check: dt.datetime
    last_state_change: dt.datetime

    @property
    def state_label(self) -> ServiceStateLabel:
        match self.state:
            case ServiceState.OK:
                return "OK"
            case ServiceState.WARN:
                return "WARN"
            case ServiceState.CRIT:
                return "CRIT"
            case ServiceState.UNKN:
                return "UNKN"
            case _:
                assert_never(self.state)
