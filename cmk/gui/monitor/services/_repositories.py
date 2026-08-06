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

from ._models import Service, ServiceFilter, ServiceOverview, ServiceSort


class HostServicesRepository(Protocol):
    def host_exists(self, hostname: str) -> bool:
        """Check whether the host exists in your environment."""
        ...

    def get_overview(self, *, hostname: str, service_name: str, site_id: str) -> ServiceOverview:
        """Fetch the overview of a single service of a host."""
        ...

    def fetch(
        self,
        hostname: str,
        *,
        limit: int | None,
        query: str,
        sorters: Sequence[ServiceSort],
        filters: ServiceFilter,
    ) -> Sequence[Service]:
        """Fetch services of a host."""
        ...

    def count_total(self, hostname: str) -> int:
        """Count the total services of a host in your environment."""
        ...

    def count_matched(self, hostname: str, *, query: str, filters: ServiceFilter) -> int:
        """Count the services of a host matching the given criteria."""
        ...
