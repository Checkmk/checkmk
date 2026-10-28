#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Literal

type ServiceStateName = Literal["ok", "warn", "crit", "unkn", "pend"]


@dataclass(frozen=True)
class HostName:
    pattern: str


@dataclass(frozen=True)
class HostAlias:
    pattern: str


@dataclass(frozen=True)
class HostAddress:
    pattern: str


@dataclass(frozen=True)
class HostGroup:
    name: str


@dataclass(frozen=True)
class HostLabel:
    key: str
    # None if only a key prefix was given, e.g. ``hl:cmk/aws*``
    value: str | None


@dataclass(frozen=True)
class HostTag:
    # None if only the tag was given, e.g. ``tg:prod``
    group: str | None
    tag: str


@dataclass(frozen=True)
class HostFolder:
    path: str


@dataclass(frozen=True)
class ServiceName:
    pattern: str


@dataclass(frozen=True)
class ServiceGroup:
    name: str


@dataclass(frozen=True)
class ServiceState:
    state: ServiceStateName


@dataclass(frozen=True)
class ServiceLabel:
    key: str
    # None if only a key prefix was given, e.g. ``sl:cmk/aws*``
    value: str | None


@dataclass(frozen=True)
class ServiceFolder:
    path: str


type Term = (
    HostName
    | HostAlias
    | HostAddress
    | HostGroup
    | HostLabel
    | HostTag
    | HostFolder
    | ServiceName
    | ServiceGroup
    | ServiceState
    | ServiceLabel
    | ServiceFolder
)


@dataclass(frozen=True)
class PrefixedSearch:
    """A query with prefixes, e.g. ``h:web h:db s:cpu``

    The terms of a clause share their prefix and are or-ed, the clauses are and-ed. Tags and
    labels are and-ed, so each of them is a clause of its own.
    """

    clauses: tuple[tuple[Term, ...], ...]


@dataclass(frozen=True)
class UnprefixedSearch:
    """A query without prefix, e.g. ``web``

    The pattern is meant for what the global search dropdown searches without prefix: host name,
    alias and address, and service name. Which of them a page filters on is up to the caller.
    ``text`` is the query the pattern is made of, for a page that takes it as typed.
    """

    text: str
    pattern: str


type SearchSpec = PrefixedSearch | UnprefixedSearch


class UnsupportedSearchError(ValueError):
    """Raised when a page can't filter on a search spec, e.g. All hosts on a service term."""
