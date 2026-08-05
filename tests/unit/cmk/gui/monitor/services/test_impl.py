#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.gui.monitor.services._impl import _build_primary_sort, LiveStatusHostServicesRepository
from cmk.gui.monitor.services._models import ServiceSort, ServiceSortColumn, ServiceSortDirection
from cmk.livestatus_client.testing import expect_single_query

# "foo-server-01" matches no row in the default hosts/services test-data, so queries against it
# return an empty result. This lets us assert on the exact query text without also needing to
# supply full row data for every column the query touches.
_UNKNOWN_HOSTNAME = "foo-server-01"
_SERVICES_COLUMNS = "description host_name state plugin_output last_check last_state_change"
_DEFAULT_ORDER_BY = "OrderBy: description asc"


def test_fetch_filters_by_exact_hostname_and_applies_limit() -> None:
    with expect_single_query(
        f"GET services\nColumns: {_SERVICES_COLUMNS}\n"
        f"Filter: host_name = {_UNKNOWN_HOSTNAME}\n{_DEFAULT_ORDER_BY}\nLimit: 500",
    ) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        repo.fetch(_UNKNOWN_HOSTNAME, limit=500, query="", sorters=[])


def test_fetch_without_limit_omits_limit_header() -> None:
    with expect_single_query(
        f"GET services\nColumns: {_SERVICES_COLUMNS}\n"
        f"Filter: host_name = {_UNKNOWN_HOSTNAME}\n{_DEFAULT_ORDER_BY}",
        match_type="ellipsis",
    ) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        repo.fetch(_UNKNOWN_HOSTNAME, limit=None, query="", sorters=[])


def test_fetch_orders_by_the_primary_sorter() -> None:
    with expect_single_query(
        f"GET services\nColumns: {_SERVICES_COLUMNS}\n"
        f"Filter: host_name = {_UNKNOWN_HOSTNAME}\nOrderBy: state desc",
        match_type="ellipsis",
    ) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        repo.fetch(
            _UNKNOWN_HOSTNAME,
            limit=None,
            query="",
            sorters=[ServiceSort(ServiceSortColumn.STATE, ServiceSortDirection.DESC)],
        )


def test_fetch_filters_by_search_query_on_description() -> None:
    with expect_single_query(
        f"GET services\nColumns: {_SERVICES_COLUMNS}\n"
        f"Filter: host_name = {_UNKNOWN_HOSTNAME}\n"
        "Filter: description ~~ CPU\nAnd: 2\n"
        f"{_DEFAULT_ORDER_BY}",
        match_type="ellipsis",
    ) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        repo.fetch(_UNKNOWN_HOSTNAME, limit=None, query="CPU", sorters=[])


def test_count_matched_query_shape() -> None:
    with expect_single_query(
        f"GET services\nStats: state >= 0\n"
        f"Filter: host_name = {_UNKNOWN_HOSTNAME}\n"
        "Filter: description ~~ CPU\nAnd: 2",
    ) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        repo.count_matched(_UNKNOWN_HOSTNAME, query="CPU")


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


@pytest.mark.parametrize(
    "sorters, expected",
    [
        pytest.param(
            [],
            "OrderBy: description asc",
            id="default fallback",
        ),
        pytest.param(
            [ServiceSort(ServiceSortColumn.STATE, ServiceSortDirection.DESC)],
            "OrderBy: state desc",
            id="descending order",
        ),
        pytest.param(
            [ServiceSort(ServiceSortColumn.NAME, ServiceSortDirection.ASC)],
            "OrderBy: description asc natural",
            id="name/description handling",
        ),
        pytest.param(
            [ServiceSort(ServiceSortColumn.SUMMARY, ServiceSortDirection.ASC)],
            "OrderBy: plugin_output asc natural",
            id="summary/plugin_output handling",
        ),
        pytest.param(
            [ServiceSort(ServiceSortColumn.LAST_CHECK, ServiceSortDirection.DESC)],
            "OrderBy: last_check desc",
            id="timestamp column",
        ),
        pytest.param(
            [
                ServiceSort(ServiceSortColumn.STATE, ServiceSortDirection.DESC),
                ServiceSort(ServiceSortColumn.NAME, ServiceSortDirection.ASC),
                ServiceSort(ServiceSortColumn.SUMMARY, ServiceSortDirection.ASC),
            ],
            "OrderBy: state desc",
            id="only first sorter used",
        ),
    ],
)
def test_build_primary_sort(sorters: Sequence[ServiceSort], expected: str) -> None:
    assert _build_primary_sort(sorters) == expected
