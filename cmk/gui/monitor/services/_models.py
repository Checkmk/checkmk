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
from collections.abc import Mapping
from typing import assert_never, Literal, NewType, override, Self

from cmk.ruleset_matcher.labels import LabelSource

type UnixTimestamp = int
"""An instant as whole seconds since the epoch (UTC)."""

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
class ServiceLabelValue:
    value: str
    source: LabelSource

    @classmethod
    def by_label(
        cls, values: Mapping[str, str], sources: Mapping[str, LabelSource]
    ) -> dict[str, Self]:
        return {key: cls(value=value, source=sources[key]) for key, value in values.items()}


@dataclasses.dataclass(frozen=True)
class Service:
    name: str
    state: ServiceState
    acknowledged: bool
    in_downtime: bool
    notifications_enabled: bool
    is_flapping: bool
    stale: bool
    summary: str
    last_check: UnixTimestamp | None
    last_state_change: UnixTimestamp
    perf_data: str
    check_command: str
    labels: dict[str, ServiceLabelValue] | None
    tags: dict[str, str] | None
    contacts: list[str] | None
    contact_groups: list[str] | None

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
    long_output: str
    current_attempt: int
    max_check_attempts: int
    # Passive services are never scheduled, so livestatus reports no next check for them.
    next_check: UnixTimestamp | None

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


class ServiceOptionalField(enum.StrEnum):
    """Columns a caller has to ask for, because fetching them costs a livestatus column per row."""

    LABELS = "labels"
    TAGS = "tags"
    CONTACTS = "contacts"
    CONTACT_GROUPS = "contact_groups"

    @classmethod
    def options(cls) -> str:
        return ", ".join(sorted(item.value for item in cls))


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


@dataclasses.dataclass(frozen=True)
class RescheduleTarget:
    """A single service check to be forcibly rescheduled at a specific time."""

    site_id: str
    host_name: str
    description: str
    check_time: dt.datetime


# NOTE: this is intended to indicate that a stringified filter has been properly parsed into a
# specific query implementation. For now, we are only supporting Livestatus queries, but this would
# allow us to easily swap out for an alternative filter parser, e.g. SQL.
ServiceFilter = NewType("ServiceFilter", str)
