#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.monitor.services._impl import LiveStatusHostServicesRepository
from cmk.livestatus_client.testing import expect_single_query

# "foo-server-01" matches no row in the default hosts/services test-data, so queries against it
# return an empty result. This lets us assert on the exact query text without also needing to
# supply full row data for every column the query touches.
_UNKNOWN_HOSTNAME = "foo-server-01"
_SERVICES_COLUMNS = "description host_name state plugin_output last_check last_state_change"


def test_fetch_filters_by_exact_hostname_and_applies_limit() -> None:
    with expect_single_query(
        f"GET services\nColumns: {_SERVICES_COLUMNS}\n"
        f"Filter: host_name = {_UNKNOWN_HOSTNAME}\nLimit: 500",
    ) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        assert repo.fetch(_UNKNOWN_HOSTNAME, limit=500) == []


def test_fetch_without_limit_omits_limit_header() -> None:
    with expect_single_query(
        f"GET services\nColumns: {_SERVICES_COLUMNS}\nFilter: host_name = {_UNKNOWN_HOSTNAME}",
        match_type="ellipsis",
    ) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        assert repo.fetch(_UNKNOWN_HOSTNAME, limit=None) == []


def test_host_exists_returns_false_for_unknown_host() -> None:
    with expect_single_query(
        f"GET hosts\nColumns: name\nFilter: name = {_UNKNOWN_HOSTNAME}\nLimit: 1",
    ) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        assert not repo.host_exists(_UNKNOWN_HOSTNAME)


def test_host_exists_returns_true_for_known_host() -> None:
    with expect_single_query(
        "GET hosts\nColumns: name\nFilter: name = heute\nLimit: 1",
    ) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        assert repo.host_exists("heute")


def test_count_total_query_shape() -> None:
    with expect_single_query(
        f"GET services\nStats: state >= 0\nFilter: host_name = {_UNKNOWN_HOSTNAME}",
    ) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        assert repo.count_total(_UNKNOWN_HOSTNAME) == 0
