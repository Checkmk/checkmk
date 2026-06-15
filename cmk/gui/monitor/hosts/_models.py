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

type StateLabel = Literal["UP", "DOWN", "UNREACHABLE"]


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
    address: str
    alias: str
    site_id: str
    service_counts: ServiceCounts

    @property
    def state_label(self) -> StateLabel:
        match self.state:
            case HostState.UP:
                return "UP"
            case HostState.DOWN:
                return "DOWN"
            case HostState.UNREACHABLE:
                return "UNREACHABLE"
            case _:
                assert_never(self.state)


class HostSortColumn(enum.StrEnum):
    """The host attributes a host query may be sorted by."""

    NAME = "name"
    ALIAS = "alias"
    ADDRESS = "address"
    STATE = "state"
    NUM_SERVICES = "num_services"
    NUM_SERVICES_OK = "num_services_ok"
    NUM_SERVICES_WARN = "num_services_warn"
    NUM_SERVICES_CRIT = "num_services_crit"
    NUM_SERVICES_UNKNOWN = "num_services_unknown"
    NUM_SERVICES_PENDING = "num_services_pending"

    @classmethod
    def options(cls) -> str:
        return ", ".join(sorted(item.value for item in cls))


class HostSortDirection(enum.StrEnum):
    """The direction a host query may be sorted in."""

    ASC = "asc"
    DESC = "desc"

    @classmethod
    def options(cls) -> str:
        return ", ".join(sorted(item.value for item in cls))


@dataclasses.dataclass(frozen=True)
class HostSort:
    """A single-column sort requested for a host query."""

    column: HostSortColumn
    direction: HostSortDirection

    def __str__(self) -> str:
        return f"{self.column.value}:{self.direction.value}"
