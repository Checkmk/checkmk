#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence, Set
from contextlib import contextmanager

from polyfactory.decorators import post_generated
from polyfactory.factories import DataclassFactory

from cmk.ccc.user import UserId
from cmk.gui.monitor.hosts._exceptions import HostNotFoundError
from cmk.gui.monitor.hosts._models import (
    Event,
    Host,
    HostFilter,
    HostOptionalField,
    HostSort,
    RelatedHost,
    UnixTimestamp,
)
from cmk.gui.monitor.hosts._repositories import EventRepository, HostRepository
from cmk.gui.permissions import permission_registry
from cmk.gui.role_types import BuiltInUserRole
from cmk.gui.session_context import UserContext
from cmk.gui.utils.host_relation_kinds import RELATION_KINDS
from cmk.gui.utils.host_relations import RelationDirection
from cmk.gui.utils.roles import UserPermissions


class RelatedHostFactory(DataclassFactory[RelatedHost]):
    """A relation whoever reads it can place.

    ``kind`` is a plain string on the domain object - a core may report one of a later version -
    but a host built here stands for one this version resolved, and only such a relation has an
    end to name it by.
    """

    __check_model__ = False
    __set_as_default_factory_for_type__ = True

    @classmethod
    def kind(cls) -> str:
        return cls.__random__.choice(list(RELATION_KINDS))

    @post_generated
    @classmethod
    def direction(cls, kind: str) -> RelationDirection:
        return cls.__random__.choice(list(RELATION_KINDS[kind].directions()))


class HostFactory(DataclassFactory[Host]):
    __check_model__ = False
    # A host built here stands for one whose columns were all read, so the optional-when-unread
    # fields always carry a value.
    __allow_none_optionals__ = False


def get_fake_host_repository(
    *,
    n_hosts: int = 0,
    hostnames: Sequence[str] = (),
    hosts: Sequence[Host] | None = None,
) -> HostRepository:
    class HostFakeRepository:
        def __init__(self) -> None:
            self._hosts = (
                list(hosts)
                if hosts is not None
                else [
                    *(HostFactory.build(name=name) for name in hostnames),
                    *(HostFactory.build() for _ in range(n_hosts)),
                ]
            )
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
            query: str,  # noqa: ARG002
            sorters: Sequence[HostSort],  # noqa: ARG002
            filters: HostFilter,  # noqa: ARG002
            fields: Set[HostOptionalField] = frozenset(),  # noqa: ARG002
            visible_relations: frozenset[tuple[str, str]] | None = None,  # noqa: ARG002
        ) -> Sequence[Host]:
            return self._hosts[:limit]

        def visible_relation_hosts(
            self,
            *,
            fields: Set[HostOptionalField],
            sorters: Sequence[HostSort],  # noqa: ARG002
        ) -> frozenset[tuple[str, str]] | None:
            if HostOptionalField.NUM_RELATIONS not in fields:
                return None
            return frozenset((host.site_id, host.name) for host in self._hosts)

        def get_overview(self, *, hostname: str, site_id: str) -> Host:
            try:
                return self._host_overviews[(site_id, hostname)]
            except KeyError:
                raise HostNotFoundError("Host not found") from None

        def count_total(self) -> int:
            return len(self._hosts)

        def count_matched(
            self,
            *,
            query: str,  # noqa: ARG002
            filters: HostFilter,  # noqa: ARG002
            fields: Set[HostOptionalField],  # noqa: ARG002
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
            hostname: str,  # noqa: ARG002
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


@contextmanager
def login_with(permissions: dict[str, bool]) -> Iterator[None]:
    """A logged-in user whose role spells out exactly these permissions."""
    role: BuiltInUserRole = {"alias": "Test", "permissions": permissions, "builtin": True}
    with UserContext(
        UserId("test"), UserPermissions({"user": role}, permission_registry, {}, ["user"])
    ):
        yield
