#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from polyfactory.factories import DataclassFactory

from cmk.gui.monitor.services._exceptions import ServiceNotFoundError
from cmk.gui.monitor.services._models import (
    Service,
    ServiceFilter,
    ServiceOverview,
    ServiceSort,
)
from cmk.gui.monitor.services._repositories import HostServicesRepository
from cmk.gui.monitor.services._sorting import service_sorter

KNOWN_HOSTNAME = "web-server-01"
KNOWN_SITE_ID = "local"


class ServiceFactory(DataclassFactory[Service]):
    __check_model__ = False


class ServiceOverviewFactory(DataclassFactory[ServiceOverview]):
    __check_model__ = False


def get_fake_host_services_repository(
    *, n_services: int, names: Sequence[str] | None = None
) -> HostServicesRepository:
    class HostServicesFakeRepository:
        def __init__(self) -> None:
            self._services = [
                ServiceFactory.build() if names is None else ServiceFactory.build(name=names[i])
                for i in range(n_services)
            ]
            self._service_overviews = {
                (KNOWN_SITE_ID, KNOWN_HOSTNAME, s.name): ServiceOverviewFactory.build(
                    site_id=KNOWN_SITE_ID, host_name=KNOWN_HOSTNAME, name=s.name
                )
                for s in self._services
            }

        def host_exists(self, hostname: str) -> bool:
            return hostname == KNOWN_HOSTNAME

        def get_overview(
            self, *, hostname: str, service_name: str, site_id: str
        ) -> ServiceOverview:
            try:
                return self._service_overviews[(site_id, hostname, service_name)]
            except KeyError:
                raise ServiceNotFoundError("Service not found") from None

        def fetch(
            self,
            hostname: str,
            *,
            limit: int | None,
            query: str,
            sorters: Sequence[ServiceSort],
            filters: ServiceFilter,
        ) -> Sequence[Service]:
            matches = [s for s in self._services if query.lower() in s.name.lower()]
            return sorted(matches, key=service_sorter(sorters))[:limit]

        def count_total(self, hostname: str) -> int:
            return len(self._services)

        def count_matched(self, hostname: str, *, query: str, filters: ServiceFilter) -> int:
            # Not implementing filter matching as we don't need to test a fake implementation of
            # this.
            return len([s for s in self._services if query.lower() in s.name.lower()])

    return HostServicesFakeRepository()
