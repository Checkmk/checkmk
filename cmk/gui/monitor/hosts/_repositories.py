#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Define repository interfaces for fetching from data sources.

These are intentionally only protocols as they are meant to only signify what sort of domain data
they will return. This allows us to pass stubs when testing our applications.
"""

from collections.abc import Sequence
from typing import Protocol

from ._models import Host, HostFilter, HostSort


class HostRepository(Protocol):
    def fetch(
        self,
        *,
        limit: int,
        search_query: str = "",
        sorters: Sequence[HostSort],
        filters: HostFilter,
    ) -> Sequence[Host]:
        """Fetch hosts based on filter criteria.

        ``search_query`` is an already whitespace-stripped free-text search. When empty, no search
        filter is applied.
        """
        ...

    def count(self, *, search_query: str = "", filters: HostFilter) -> int:
        """Count the hosts matching the given criteria.

        ``search_query`` is an already whitespace-stripped free-text search. When empty, the total
        number of hosts is returned.
        """
        ...
