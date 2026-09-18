#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
