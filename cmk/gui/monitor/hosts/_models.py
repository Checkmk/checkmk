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

type HostStateLabel = Literal["UP", "DOWN", "UNREACHABLE"]


class HostState(enum.IntEnum):
    UP = 0
    DOWN = 1
    UNREACHABLE = 2


@dataclasses.dataclass(frozen=True)
class ServiceCounts:
    total: int
    ok: int
    warn: int
    crit: int
    unknown: int
    pending: int


@dataclasses.dataclass(frozen=True)
class HostLabelValue:
    value: str
    source: LabelSource

    @classmethod
    def by_label(
        cls, values: Mapping[str, str], sources: Mapping[str, LabelSource]
    ) -> dict[str, Self]:
        return {key: cls(value=value, source=sources[key]) for key, value in values.items()}


@dataclasses.dataclass(frozen=True)
class Host:
    """A host row.

    Every field that a caller has to ask for is `None` when it was not read, which is what
    tells "the host has no alias" apart from "nobody asked for the alias".
    """

    name: str
    state: HostState
    address: str | None
    alias: str | None
    site_id: str
    service_counts: ServiceCounts | None
    acknowledged: bool
    in_downtime: bool
    folder: str | None
    last_check: dt.datetime | None
    last_state_change: dt.datetime | None
    labels: dict[str, HostLabelValue] | None

    @property
    def state_label(self) -> HostStateLabel:
        match self.state:
            case HostState.UP:
                return "UP"
            case HostState.DOWN:
                return "DOWN"
            case HostState.UNREACHABLE:
                return "UNREACHABLE"
            case _:
                assert_never(self.state)


@dataclasses.dataclass(frozen=True)
class HostOverview(Host):
    customer: str | None
    contact_groups: list[str] = dataclasses.field(default_factory=list)
    tags: dict[str, str] = dataclasses.field(default_factory=dict)


class HostOptionalField(enum.StrEnum):
    ADDRESS = "address"
    ALIAS = "alias"
    NUM_SERVICES = "num_services"
    NUM_SERVICES_OK = "num_services_ok"
    NUM_SERVICES_WARN = "num_services_warn"
    NUM_SERVICES_CRIT = "num_services_crit"
    NUM_SERVICES_UNKNOWN = "num_services_unknown"
    NUM_SERVICES_PENDING = "num_services_pending"
    FOLDER = "folder"
    LAST_CHECK = "last_check"
    LAST_STATE_CHANGE = "last_state_change"
    LABELS = "labels"

    @classmethod
    def options(cls) -> str:
        return ", ".join(sorted(item.value for item in cls))


class HostSortColumn(enum.StrEnum):
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
    FOLDER = "folder"
    SITE_ID = "site_id"
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
        HostSortColumn.NAME,
        HostSortColumn.ALIAS,
        HostSortColumn.ADDRESS,
        HostSortColumn.FOLDER,
        HostSortColumn.SITE_ID,
    }
)


class HostSortDirection(enum.StrEnum):
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

    @override
    def __str__(self) -> str:
        return f"{self.column.value}:{self.direction.value}"


@dataclasses.dataclass(frozen=True)
class RescheduleTarget:
    """A single host check to be forcibly rescheduled at a specific time."""

    site_id: str
    host_name: str
    check_time: dt.datetime


# NOTE: this is intended to indicate that a stringified filter has been properly parsed into a
# specific query implementation. For now, we are only supporting Livestatus queries, but this would
# allow us to easily swap out for an alternative filter parser, e.g. SQL.
HostFilter = NewType("HostFilter", str)
