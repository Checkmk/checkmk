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
from typing import assert_never, Literal, NewType, override

type ServiceStateLabel = Literal["OK", "WARN", "CRIT", "UNKNOWN"]

type HostStateLabel = Literal["UP", "DOWN", "UNREACHABLE"]


class ServiceState(enum.IntEnum):
    OK = 0
    WARN = 1
    CRIT = 2
    UNKNOWN = 3


class HostState(enum.IntEnum):
    UP = 0
    DOWN = 1
    UNREACHABLE = 2


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
            case ServiceState.UNKNOWN:
                return "UNKNOWN"
            case _:
                assert_never(self.state)


@dataclasses.dataclass(frozen=True)
class ServiceOverview(Service):
    host_name: str
    host_alias: str
    host_state: HostState
    host_acknowledged: bool
    host_in_downtime: bool
    site_id: str
    acknowledged: bool
    in_downtime: bool
    notifications_enabled: bool
    contact_groups: list[str]
    long_output: str
    current_attempt: int
    max_check_attempts: int
    # Passive services are never scheduled, so livestatus reports no next check for them.
    next_check: dt.datetime | None

    @property
    def host_state_label(self) -> HostStateLabel:
        match self.host_state:
            case HostState.UP:
                return "UP"
            case HostState.DOWN:
                return "DOWN"
            case HostState.UNREACHABLE:
                return "UNREACHABLE"
            case _:
                assert_never(self.host_state)


class ServiceSortColumn(enum.StrEnum):
    NAME = "name"
    STATE = "state"
    SUMMARY = "summary"
    LAST_CHECK = "last_check"
    LAST_STATE_CHANGE = "last_state_change"

    @classmethod
    def options(cls) -> str:
        return ", ".join(sorted(item.value for item in cls))

    @property
    def natural_sort(self) -> bool:
        return self in _NATURAL_SORT_COLUMNS


_NATURAL_SORT_COLUMNS = frozenset(
    {
        ServiceSortColumn.NAME,
        ServiceSortColumn.SUMMARY,
    }
)


class ServiceSortDirection(enum.StrEnum):
    ASC = "asc"
    DESC = "desc"

    @classmethod
    def options(cls) -> str:
        return ", ".join(sorted(item.value for item in cls))


@dataclasses.dataclass(frozen=True)
class ServiceSort:
    """A single-column sort requested for a service query."""

    column: ServiceSortColumn
    direction: ServiceSortDirection

    @override
    def __str__(self) -> str:
        return f"{self.column.value}:{self.direction.value}"


# NOTE: this is intended to indicate that a stringified filter has been properly parsed into a
# specific query implementation. For now, we are only supporting Livestatus queries, but this would
# allow us to easily swap out for an alternative filter parser, e.g. SQL.
ServiceFilter = NewType("ServiceFilter", str)
