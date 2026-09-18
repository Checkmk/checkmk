#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Define repository interfaces for fetching from data sources.

These are intentionally only protocols as they are meant to only signify what sort of domain data
they will return. This allows us to pass stubs when testing our applications.
"""

from collections.abc import Sequence, Set
from typing import Protocol

from ._models import (
    Event,
    Host,
    HostFilter,
    HostOptionalField,
    HostSort,
    UnixTimestamp,
)


class HostRepository(Protocol):
    def host_exists(self, hostname: str) -> bool:
        """Check whether the host exists in your environment."""
        ...

    def fetch(
        self,
        *,
        limit: int | None,
        query: str,
        sorters: Sequence[HostSort],
        filters: HostFilter,
        fields: Set[HostOptionalField],
    ) -> Sequence[Host]:
        """Fetch hosts, reading only the columns `fields` and `sorters` need."""
        ...

    def get_overview(self, *, hostname: str, site_id: str) -> Host:
        """Get host overview by identifiers, reading every column."""
        ...

    def count_total(self) -> int:
        """Count the total hosts in your environment."""
        ...

    def count_matched(
        self, *, query: str, filters: HostFilter, fields: Set[HostOptionalField]
    ) -> int:
        """Count the hosts matching the given criteria, searching `fields` alongside the name."""
        ...


class EventRepository(Protocol):
    def fetch(
        self,
        *,
        hostname: str,
        service_name: str | None,
        since: UnixTimestamp,
        limit: int,
    ) -> Sequence[Event]:
        """Fetch the events of a host, newest first, reading at most `limit` rows.

        Passing a `service_name` narrows the result to that service's events; omitting it returns
        the host's own events alongside those of all its services.
        """
        ...
