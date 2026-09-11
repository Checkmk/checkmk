#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.gui.monitor.hosts._impl import _wato_folder_from_filename, LiveStatusHostRepository
from cmk.gui.monitor.hosts._models import HostFilter
from cmk.livestatus_client.testing import expect_single_query


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("/wato/hosts.mk", "/"),
        ("/wato/network/switches/hosts.mk", "/network/switches"),
        ("/wato/network/hosts.mk", "/network"),
        ("/omd/sites/heute/etc/nagios/conf.d/hosts.mk", None),
        ("/wato/network/switches/other.mk", None),
    ],
)
def test_wato_folder_from_filename(filename: str, expected: str | None) -> None:
    assert _wato_folder_from_filename(filename) == expected


def test_count_matched_keeps_a_stray_carriage_return_on_one_line() -> None:
    # Regression test: a "\r" embedded in a filter value must not turn into a Livestatus line
    # break when the hand-assembled Stats query is joined with "\n" - only a real "\n" may do
    # that. Livestatus itself treats "\r" as ordinary data, and so must this query.
    filters = HostFilter("Filter: name ~~ evil\rmore")
    with expect_single_query(
        "GET hosts\nStats: state >= 0\nFilter: name ~~ evil\rmore",
        match_type="strict",
    ) as live:
        repo = LiveStatusHostRepository(connection=live)
        repo.count_matched(query="", filters=filters)
