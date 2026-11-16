#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Collection, Iterable

from cmk.livestatus_client import LocalConnection
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables import Hosts

# The services that a host has before its first service discovery
_DEFAULT_SERVICES = frozenset({"Check_MK", "Check_MK Discovery"})

type ServicesPerHostReader = Callable[[], Iterable[Collection[str]]]


def collect(services_per_host: Iterable[Collection[str]]) -> int:
    return sum(1 for services in services_per_host if _DEFAULT_SERVICES.issuperset(services))


def read_services_per_host() -> list[list[str]]:
    rows = LocalConnection().query(Query([Hosts.services]))
    return [row[0] for row in rows]
