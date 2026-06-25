#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pins the shared GUI↔daemon autocomplete query builder (cmk.maps.shared.autocomplete)."""

from cmk.maps.shared.autocomplete import object_autocomplete_query, unique_names

# The tests use a no-op escaper to keep assertions readable; the real callers
# pass lqencode.
_NO_ESCAPE = str


def test_unknown_type_returns_none() -> None:
    assert object_autocomplete_query("bogus", escape=_NO_ESCAPE, limit=100) is None


def test_host_query_is_single_column() -> None:
    assert (
        object_autocomplete_query("host", escape=_NO_ESCAPE, limit=50)
        == "GET hosts\nColumns: name\nLimit: 50\n"
    )


def test_service_query_selects_the_bare_description() -> None:
    # The picker binds ``service_description``, so the column it reads must be
    # the description alone — never a "host;service" pair the object would
    # then store verbatim.
    query = object_autocomplete_query("service", escape=_NO_ESCAPE, limit=50, host="h1")
    assert query is not None
    assert query.startswith("GET services\nColumns: description\n")


def test_service_query_scopes_host_and_search() -> None:
    query = object_autocomplete_query(
        "service", escape=_NO_ESCAPE, limit=50, host="h1", search="cpu"
    )
    assert query is not None
    assert "Filter: host_name = h1\n" in query
    assert "Filter: description ~~ cpu\n" in query
    assert query.endswith("Limit: 50\n")


def test_search_is_regex_escaped_through_the_escaper() -> None:
    # The typed substring is regex-escaped before the escaper sees it, so a
    # literal "(" can't make Livestatus reject the query.
    query = object_autocomplete_query("host", escape=_NO_ESCAPE, limit=10, search="a(b")
    assert query is not None
    assert "Filter: name ~~ a\\(b\n" in query


def test_no_search_omits_name_filter() -> None:
    query = object_autocomplete_query("hostgroup", escape=_NO_ESCAPE, limit=10)
    assert query is not None
    assert "~~" not in query


def test_unique_names_drops_repeats_in_query_order() -> None:
    # An unscoped service search reads the same description from every host
    # running it; the picker offers a name, so the repeats carry nothing.
    assert unique_names(["CPU", "Mem", "CPU", "Disk", "Mem"]) == ["CPU", "Mem", "Disk"]
