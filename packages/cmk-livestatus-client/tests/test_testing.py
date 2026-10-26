#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.livestatus_client import MultiSiteConnection
from cmk.livestatus_client.testing import (
    mock_livestatus_communication,
    mock_site_configurations,
    MockLiveStatusConnection,
)

_QUERY = "GET hosts\nColumns: name"


def test_an_unreachable_site_is_listed_among_the_dead_sites() -> None:
    with mock_livestatus_communication() as live:
        live.set_sites(["NO_SITE", "remote"])
        live.make_site_unreachable("remote")
        # Expected on every site; leaving the block without complaint proves the dead one was left
        # out.
        live.expect_query("GET hosts\nColumns: name")
        with live(expect_status_query=False):
            connection = MultiSiteConnection(sites=mock_site_configurations(live.sites))
            connection.query("GET hosts\nColumns: name")

    assert sorted(connection.dead_sites()) == ["remote"]


def test_a_site_with_expected_queries_cannot_become_unreachable() -> None:
    with mock_livestatus_communication() as live:
        live.expect_query("GET hosts")

        with pytest.raises(ValueError, match="remote"):
            live.make_site_unreachable("remote")


def test_a_query_expected_on_an_unreachable_site_is_rejected() -> None:
    with mock_livestatus_communication() as live:
        live.make_site_unreachable("remote")

        with pytest.raises(ValueError, match="remote"):
            live.expect_query("GET hosts", sites=["remote"])


def test_a_command_is_rejected_when_the_first_site_is_unreachable() -> None:
    with mock_livestatus_communication() as live:
        live.make_site_unreachable("NO_SITE")

        with pytest.raises(ValueError, match="NO_SITE"):
            live.expect_query("COMMAND [1] DISABLE_NOTIFICATIONS")


def test_the_combined_result_leaves_out_an_unreachable_site() -> None:
    live = MockLiveStatusConnection()
    live.set_sites(["NO_SITE", "remote"])
    live.add_table("hosts", [{"name": "heute"}])
    live.make_site_unreachable("remote")
    live.expect_query("GET hosts\nColumns: name")

    assert live.result_of_next_query("GET hosts\nColumns: name")[0] == [["heute"]]


def test_an_expected_error_is_answered_like_the_core_answers_it() -> None:
    live = MockLiveStatusConnection()
    live.expect_query(
        _QUERY, sites=live.sites[:1], error=(413, "Maximum query time of 20 seconds exceeded!")
    )

    with live(expect_status_query=False):
        site = live.create_socket(None, None)
        site.sendall(f"{_QUERY}\n\n".encode())

        assert site.recv(16) == b"413          43\n"
        assert site.recv(43) == b"Maximum query time of 20 seconds exceeded!\n"


def test_an_error_answers_only_its_own_query() -> None:
    live = MockLiveStatusConnection()
    live.expect_query(_QUERY, sites=live.sites[:1], error=(400, "invalid regular expression"))
    live.expect_query(_QUERY, sites=live.sites[:1])

    with live(expect_status_query=False):
        site = live.create_socket(None, None)
        site.sendall(f"{_QUERY}\n\n".encode())
        site.recv(16 + len("invalid regular expression\n"))
        site.sendall(f"{_QUERY}\n\n".encode())

        assert site.recv(16).startswith(b"200 ")
