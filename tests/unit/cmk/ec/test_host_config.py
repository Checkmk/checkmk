#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import pytest

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ec.core_queries import HostInfo
from cmk.ec.host_config import HostConfig

type Rows = Sequence[Sequence[Any]]


@dataclass(frozen=True)
class QueryAndResponse:
    query_lines: Iterable[str]
    response: Rows


class ObservedConnection:
    @contextmanager
    def expect(self, queries: Iterable[QueryAndResponse]) -> Iterator[None]:
        self._queries = list(reversed(list(queries)))
        yield
        assert not self._queries

    def query(self, query: str) -> Rows:
        expected_query = self._queries.pop()
        assert query == "\n".join(expected_query.query_lines)
        return expected_query.response


def status_query(now: int) -> QueryAndResponse:
    return QueryAndResponse(
        query_lines=[
            "GET status",
            "Columns: program_start",
        ],
        response=[[now]],
    )


def hosts_query(heute_alias: str = "heute alias") -> QueryAndResponse:
    return QueryAndResponse(
        query_lines=[
            "GET hosts",
            "Columns: name alias address custom_variables contacts contact_groups groups",
        ],
        response=[
            [
                "heute",
                heute_alias,
                "127.0.0.1",
                {
                    "FILENAME": "/wato/hosts.mk",
                    "ADDRESS_FAMILY": "4",
                    "ADDRESS_4": "127.0.0.1",
                    "ADDRESS_6": "",
                    "TAGS": "/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp",
                },
                [],
                ["all"],
                ["custom-group"],
            ],
            [
                "example.com",
                "example.com alias",
                "server.example.com",
                {
                    "FILENAME": "/wato/hosts.mk",
                    "ADDRESS_FAMILY": "4",
                    "ADDRESS_4": "127.0.0.1",
                    "ADDRESS_6": "",
                    "TAGS": "/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp",
                },
                [],
                ["all"],
                [],
            ],
        ],
    )


@pytest.mark.parametrize(
    "hostname, result",
    [
        (
            HostName("heute"),
            HostInfo(
                name=HostName("heute"),
                alias="heute alias",
                address=HostAddress("127.0.0.1"),
                custom_variables={
                    "FILENAME": "/wato/hosts.mk",
                    "ADDRESS_FAMILY": "4",
                    "ADDRESS_4": "127.0.0.1",
                    "ADDRESS_6": "",
                    "TAGS": "/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp",
                },
                contacts=set(),
                contact_groups={"all"},
                host_groups={"custom-group"},
            ),
        ),
        (HostName("HEUTE"), None),
        (HostName("127.0.0.1"), None),
    ],
)
def test_host_config(hostname: HostName, result: HostInfo | None) -> None:
    connection = ObservedConnection()
    host_config = HostConfig(logging.getLogger("cmk.mkeventd.EventServer"), connection)
    now = 1764329250

    with connection.expect([status_query(now), hosts_query()]):
        assert host_config.get_config_for_host(hostname) == result

    # Data is cached and not queried twice.
    with connection.expect([status_query(now)]):
        assert host_config.get_config_for_host(hostname) == result


@pytest.mark.parametrize(
    "search_term, result",
    [
        ("heute", HostName("heute")),
        ("HEUTE", HostName("heute")),
        ("127.0.0.1", HostName("heute")),
        ("server.example.com", HostName("example.com")),
        ("SERVER.example.com", HostName("example.com")),
        ("not-matching", None),
        ("heute alias", HostName("heute")),
    ],
)
def test_host_config_get_canonical_name(search_term: str, result: HostName | None) -> None:
    connection = ObservedConnection()
    host_config = HostConfig(logging.getLogger("cmk.mkeventd.EventServer"), connection)
    now = 1764329250

    with connection.expect([status_query(now), hosts_query()]):
        assert host_config.get_canonical_name(search_term) == result

    # Data is cached and not queried twice.
    with connection.expect([status_query(now)]):
        assert host_config.get_canonical_name(search_term) == result


def test_host_config_get_canonical_name_is_cached_updated() -> None:
    connection = ObservedConnection()
    host_config = HostConfig(logging.getLogger("cmk.mkeventd.EventServer"), connection)
    now = 1764329250

    with connection.expect([status_query(now), hosts_query()]):
        assert host_config.get_canonical_name("heute alias") == HostName("heute")

    # Simulate config update
    with connection.expect([status_query(now + 10), hosts_query("new alias")]):
        assert host_config.get_canonical_name("heute alias") is None

    with connection.expect([status_query(now + 10)]):
        assert host_config.get_canonical_name("new alias") == HostName("heute")
