#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence, Set

from polyfactory.factories import DataclassFactory

from cmk.gui.monitor.hosts._exceptions import HostNotFoundError
from cmk.gui.monitor.hosts._models import (
    Event,
    Host,
    HostFilter,
    HostOptionalField,
    HostSort,
    UnixTimestamp,
)
from cmk.gui.monitor.hosts._repositories import EventRepository, HostRepository


class HostFactory(DataclassFactory[Host]):
    __check_model__ = False
    # A host built here stands for one whose columns were all read, so the optional-when-unread
    # fields always carry a value.
    __allow_none_optionals__ = False


def get_fake_host_repository(*, n_hosts: int = 0, hostnames: Sequence[str] = ()) -> HostRepository:
    class HostFakeRepository:
        def __init__(self) -> None:
            self._hosts = [
                *(HostFactory.build(name=name) for name in hostnames),
                *(HostFactory.build() for _ in range(n_hosts)),
            ]
            self._host_overviews = {
                (h.site_id, h.name): HostFactory.build(site_id=h.site_id, name=h.name)
                for h in self._hosts
            }

        def host_exists(self, hostname: str) -> bool:
            return any(host.name == hostname for host in self._hosts)

        def fetch(
            self,
            *,
            limit: int | None,
            query: str,
            sorters: Sequence[HostSort],
            filters: HostFilter,
            fields: Set[HostOptionalField] = frozenset(),
        ) -> Sequence[Host]:
            return self._hosts[:limit]

        def get_overview(self, *, hostname: str, site_id: str) -> Host:
            try:
                return self._host_overviews[(site_id, hostname)]
            except KeyError:
                raise HostNotFoundError("Host not found") from None

        def count_total(self) -> int:
            return len(self._hosts)

        def count_matched(
            self, *, query: str, filters: HostFilter, fields: Set[HostOptionalField]
        ) -> int:
            # Not implementing this as we don't need to test a fake implementation of this.
            return self.count_total()

    return HostFakeRepository()


class EventFactory(DataclassFactory[Event]):
    __check_model__ = False
    __allow_none_optionals__ = False


def get_fake_event_repository(events: Sequence[Event]) -> EventRepository:
    class EventFakeRepository:
        def fetch(
            self,
            *,
            hostname: str,
            service_name: str | None,
            since: UnixTimestamp,
            limit: int,
        ) -> Sequence[Event]:
            matching = [
                event
                for event in events
                if event.time >= since
                and (service_name is None or event.service_name == service_name)
            ]
            return sorted(matching, key=lambda event: event.recency, reverse=True)[:limit]

    return EventFakeRepository()
