#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.livestatus_client._connection import Query as ConnectionQuery
from cmk.livestatus_client._connection import SingleSiteConnection
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables import Hosts


def test_extra_headers_only_split_on_newline() -> None:
    # Regression test: Query used to normalize extra_headers with str.splitlines(), which also
    # breaks on "\r" and other Unicode line/paragraph separators Livestatus itself does not treat
    # as boundaries. A header carrying one of those characters must stay a single line - if it
    # were split apart here and rejoined with "\n" in compile(), it would turn into a real
    # Livestatus line break, splitting one request into two on the wire.
    query = Query([Hosts.name], extra_headers=["Limit: 1\rmore"])

    assert query.extra_headers == ["Limit: 1\rmore"]
    assert query.compile() == "GET hosts\nColumns: name\nLimit: 1\rmore"


def test_extra_headers_split_on_real_newline() -> None:
    query = Query([Hosts.name], extra_headers=["Filter: name = a\nFilter: name = b"])

    assert query.extra_headers == ["Filter: name = a", "Filter: name = b"]


def test_extra_headers_drop_blank_lines() -> None:
    query = Query([Hosts.name], extra_headers=["", "Limit: 1"])

    assert query.extra_headers == ["Limit: 1"]


def test_cache_header_emitted_after_table_line() -> None:
    query = Query([Hosts.name], Hosts.name == "heute", cache=True)

    assert query.compile() == "GET hosts\nCache: reload\nColumns: name\nFilter: name = heute"


def test_cache_header_absent_by_default() -> None:
    assert "Cache:" not in Query([Hosts.name]).compile()


def test_filter_keeps_cache() -> None:
    query = Query([Hosts.name], cache=True)

    assert query.filter(Hosts.name == "heute").cache is True


def test_from_string_round_trips_cache_header() -> None:
    query = Query([Hosts.name], Hosts.name == "heute", cache=True)

    assert str(Query.from_string(str(query))) == str(query)


def test_connection_strips_cache_header_when_not_allowed() -> None:
    connection = SingleSiteConnection("unix:/nonexistent", allow_cache=False)
    query = Query([Hosts.name], cache=True)

    assert "Cache:" not in connection.build_query(ConnectionQuery(query), "")


def test_connection_keeps_cache_header_when_allowed() -> None:
    connection = SingleSiteConnection("unix:/nonexistent", allow_cache=True)
    query = Query([Hosts.name], cache=True)

    assert "Cache: reload\n" in connection.build_query(ConnectionQuery(query), "")


def test_filter_keeps_extra_headers() -> None:
    query = Query([Hosts.name], extra_headers=["Limit: 5"])

    filtered = query.filter(Hosts.name == "myhost")

    assert filtered.extra_headers == ["Limit: 5"]
    assert filtered.compile() == "GET hosts\nColumns: name\nFilter: name = myhost\nLimit: 5"
