#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence, Set
from contextlib import contextmanager

from polyfactory.factories import DataclassFactory

from cmk.ccc.user import UserId
from cmk.gui.monitor.services._exceptions import ServiceNotFoundError
from cmk.gui.monitor.services._models import (
    Service,
    ServiceFilter,
    ServiceOptionalField,
    ServiceOverview,
    ServiceSort,
)
from cmk.gui.monitor.services._repositories import HostServicesRepository
from cmk.gui.monitor.services._sorting import service_sorter
from cmk.gui.permissions import all_permissions
from cmk.gui.role_types import BuiltInUserRole
from cmk.gui.session_context import UserContext
from cmk.gui.utils.roles import UserPermissions

KNOWN_HOSTNAME = "web-server-01"
KNOWN_SITE_ID = "local"


class ServiceFactory(DataclassFactory[Service]):
    __check_model__ = False
    # A service built here stands for one whose columns were all read, so the
    # optional-when-unread fields always carry a value.
    __allow_none_optionals__ = False


class ServiceOverviewFactory(DataclassFactory[ServiceOverview]):
    __check_model__ = False
    __allow_none_optionals__ = False


def get_fake_host_services_repository(
    *,
    n_services: int = 0,
    names: Sequence[str] | None = None,
    services: Sequence[Service] | None = None,
) -> HostServicesRepository:
    class HostServicesFakeRepository:
        def __init__(self) -> None:
            if services is not None:
                self._services = list(services)
            else:
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
            hostname: str,  # noqa: ARG002
            *,
            limit: int | None,
            query: str,
            sorters: Sequence[ServiceSort],
            filters: ServiceFilter,  # noqa: ARG002
            fields: Set[ServiceOptionalField] = frozenset(),  # noqa: ARG002
        ) -> Sequence[Service]:
            matches = [s for s in self._services if query.lower() in s.name.lower()]
            return sorted(matches, key=service_sorter(sorters))[:limit]

        def count_total(self, hostname: str) -> int:  # noqa: ARG002
            return len(self._services)

        def count_matched(
            self,
            hostname: str,  # noqa: ARG002
            *,
            query: str,
            filters: ServiceFilter,  # noqa: ARG002
            fields: Set[ServiceOptionalField] = frozenset(),  # noqa: ARG002
        ) -> int:
            # Not implementing filter matching as we don't need to test a fake implementation of
            # this.
            return len([s for s in self._services if query.lower() in s.name.lower()])

        def unreachable_sites(self) -> list[str]:
            return []

        def unavailable_sites(self) -> frozenset[str]:
            return frozenset()

    return HostServicesFakeRepository()


class FakeServicesRepository:
    def __init__(self, services: Sequence[Service], *, matched: int | None = None) -> None:
        self._services = list(services)
        self._matched = matched
        self.count_matched_calls = 0

    def fetch(
        self,
        *,
        limit: int | None,  # noqa: ARG002
        query: str,
        sorters: Sequence[ServiceSort],
        filters: ServiceFilter,  # noqa: ARG002
        fields: Set[ServiceOptionalField],  # noqa: ARG002
    ) -> Sequence[Service]:
        return sorted(self._matching(query), key=service_sorter(sorters))

    def count_total(self) -> int:
        return len(self._services)

    def count_matched(
        self,
        *,
        query: str,
        filters: ServiceFilter,  # noqa: ARG002
        fields: Set[ServiceOptionalField],  # noqa: ARG002
    ) -> int:
        self.count_matched_calls += 1
        return len(self._matching(query)) if self._matched is None else self._matched

    def unreachable_sites(self) -> list[str]:
        return []

    def _matching(self, query: str) -> list[Service]:
        return [s for s in self._services if query.lower() in f"{s.host_name} {s.name}".lower()]


@contextmanager
def login_with(permissions: dict[str, bool]) -> Iterator[None]:
    """A logged-in user whose role spells out exactly these permissions."""
    role: BuiltInUserRole = {"alias": "Test", "permissions": permissions, "builtin": True}
    with UserContext(
        UserId("test"),
        UserPermissions(
            {"user": role},
            all_permissions(),
            {},
            ["user"],
        ),
    ):
        yield
