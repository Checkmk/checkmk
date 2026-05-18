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
import enum
from typing import assert_never, Literal


class HostState(enum.IntEnum):
    UP = 0
    DOWN = 1
    UNREACHABLE = 2


@dataclasses.dataclass
class ServiceCounts:
    total: int
    ok: int
    warn: int
    crit: int
    unknown: int
    pending: int


@dataclasses.dataclass
class Host:
    name: str
    state: HostState
    ip: str
    alias: str
    site_id: str
    service_counts: ServiceCounts

    @property
    def state_label(self) -> Literal["UP", "DOWN", "UNREACHABLE"]:
        match self.state:
            case HostState.UP:
                return "UP"
            case HostState.DOWN:
                return "DOWN"
            case HostState.UNREACHABLE:
                return "UNREACHABLE"
            case _:
                assert_never(self.state)
