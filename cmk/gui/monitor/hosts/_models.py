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

from cmk.gui.utils.host_relations import RelationDirection
from cmk.ruleset_matcher.labels import LabelSource

type UnixTimestamp = int
"""An instant as whole seconds since the epoch (UTC)."""

type HostStateLabel = Literal["UP", "DOWN", "UNREACHABLE", "PENDING"]


class HostState(enum.IntEnum):
    UP = 0
    DOWN = 1
    UNREACHABLE = 2
    # Not a real Livestatus state: assigned to a host that has never been checked, whose raw
    # `state` column is meaningless (always 0). See ``LiveStatusHostRepository`` for where this
    # gets constructed instead of the real state.
    PENDING = 3


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


def _state_label(state: HostState) -> HostStateLabel:
    match state:
        case HostState.UP:
            return "UP"
        case HostState.DOWN:
            return "DOWN"
        case HostState.UNREACHABLE:
            return "UNREACHABLE"
        case HostState.PENDING:
            return "PENDING"
        case _:
            assert_never(state)


MAX_RESOLVED_RELATIONS = 100
"""How many of a host's relations its details resolve and show.

Nothing bounds how many relations a host has - a management board collects one per OS host that
names it - and both the query reading the counterparts' state and the response carrying their
cards grow with that number.
"""


@dataclasses.dataclass(frozen=True)
class RelatedHostHealth:
    """What the monitoring knows about a related host, i.e. what its card can render."""

    state: HostState
    service_counts: ServiceCounts

    @property
    def state_label(self) -> HostStateLabel:
        return _state_label(self.state)


@dataclasses.dataclass(frozen=True)
class RelatedHost:
    """A monitored host related to the host being shown."""

    name: str
    kind: str
    """Id of the kind of relation, as it was stored - see `cmk.gui.utils.host_relation_kinds`."""
    direction: RelationDirection
    """The end this host sits at, i.e. what it is to the host being shown."""
    site_id: str
    health: RelatedHostHealth | None
    """`None` when the site monitoring it is not available, so nothing about it is known.

    A relation whose host is gone is left out altogether instead: a reader has to be able to tell
    "cannot be reached right now" from "there is no board".
    """


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
    notifications_enabled: bool
    num_comments: int
    active_checks_disabled: bool
    passive_checks_disabled: bool
    in_notification_period: bool
    in_service_period: bool
    in_check_period: bool
    is_flapping: bool
    stale: bool
    folder: str | None
    last_check: UnixTimestamp | None
    last_state_change: UnixTimestamp | None
    labels: dict[str, HostLabelValue] | None
    tags: dict[str, str] | None
    contacts: list[str] | None
    contact_groups: list[str] | None
    num_relations: int | None = None
    """How many hosts are related to this one - all the listing shows."""
    relations: tuple[RelatedHost, ...] = ()
    """The related hosts themselves, resolved for the overview only."""
    more_relations: bool = False
    """Whether the host has relations beyond the ones in `relations`, i.e. the list was cut."""

    @property
    def state_label(self) -> HostStateLabel:
        return _state_label(self.state)


class HostOptionalField(enum.StrEnum):
    ADDRESS = "address"
    ALIAS = "alias"
    NUM_SERVICES = "num_services"
    NUM_SERVICES_OK = "num_services_ok"
    NUM_SERVICES_WARN = "num_services_warn"
    NUM_SERVICES_CRIT = "num_services_crit"
    NUM_SERVICES_UNKNOWN = "num_services_unknown"
    NUM_SERVICES_PENDING = "num_services_pending"
    NUM_RELATIONS = "num_relations"
    FOLDER = "folder"
    LAST_CHECK = "last_check"
    LAST_STATE_CHANGE = "last_state_change"
    LABELS = "labels"
    TAGS = "tags"
    CONTACTS = "contacts"
    CONTACT_GROUPS = "contact_groups"

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
    NUM_RELATIONS = "num_relations"
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


class EventClass(enum.IntEnum):
    """The monitoring log classes making up the event history of a host and its services."""

    STATE = 1
    NOTIFICATION = 3
    ALERT_HANDLER = 8


@dataclasses.dataclass(frozen=True)
class Event:
    """One monitoring log entry, belonging either to a host or to one of its services."""

    time: UnixTimestamp
    lineno: int
    type: str
    state: int
    state_type: str
    state_info: str
    command_name: str
    plugin_output: str
    service_name: str | None

    @property
    def state_information(self) -> str:
        return self.state_info or self.state_type

    @property
    def recency(self) -> tuple[UnixTimestamp, int]:
        return self.time, self.lineno


# NOTE: this is intended to indicate that a stringified filter has been properly parsed into a
# specific query implementation. For now, we are only supporting Livestatus queries, but this would
# allow us to easily swap out for an alternative filter parser, e.g. SQL.
HostFilter = NewType("HostFilter", str)
