#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.livestatus_client import MultiSiteConnection
from cmk.livestatus_client.testing import mock_livestatus_communication, mock_site_configurations


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
