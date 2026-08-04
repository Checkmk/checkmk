#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from polyfactory.factories import DataclassFactory

from cmk.gui.monitor.services._models import Service, ServiceSort
from cmk.gui.monitor.services._repositories import HostServicesRepository
from cmk.gui.monitor.services._sorting import service_sorter

KNOWN_HOSTNAME = "web-server-01"


class ServiceFactory(DataclassFactory[Service]):
    __check_model__ = False


def get_fake_host_services_repository(*, n_services: int) -> HostServicesRepository:
    class HostServicesFakeRepository:
        def __init__(self) -> None:
            self._services = [ServiceFactory.build() for _ in range(n_services)]

        def host_exists(self, hostname: str) -> bool:
            return hostname == KNOWN_HOSTNAME

        def fetch(
            self,
            hostname: str,
            *,
            limit: int | None,
            query: str,
            sorters: Sequence[ServiceSort],
        ) -> Sequence[Service]:
            matches = [s for s in self._services if query.lower() in s.name.lower()]
            return sorted(matches, key=service_sorter(sorters))[:limit]

        def count_total(self, hostname: str) -> int:
            return len(self._services)

        def count_matched(self, hostname: str, *, query: str) -> int:
            return len([s for s in self._services if query.lower() in s.name.lower()])

    return HostServicesFakeRepository()
