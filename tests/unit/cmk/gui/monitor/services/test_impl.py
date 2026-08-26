#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.gui.monitor.services._impl import (
    _build_primary_sort,
    _build_query_filter,
    _OPTIONAL_COLUMNS,
    LiveStatusHostServicesRepository,
)
from cmk.gui.monitor.services._models import (
    ServiceFilter,
    ServiceOptionalField,
    ServiceSort,
    ServiceSortColumn,
    ServiceSortDirection,
)
from cmk.livestatus_client.testing import expect_single_query
from tests.testlib.gui.web_test_app import SetConfig

# "foo-server-01" matches no row in the default hosts/services test-data, so queries against it
# return an empty result. This lets us assert on the exact query text without also needing to
# supply full row data for every column the query touches.
_UNKNOWN_HOSTNAME = "foo-server-01"
_SERVICES_COLUMNS = (
    "description host_name state plugin_output acknowledged scheduled_downtime_depth "
    "notifications_enabled is_flapping staleness last_check last_state_change perf_data "
    "check_command"
)
_DEFAULT_ORDER_BY = "OrderBy: description asc natural"


def test_fetch_filters_by_exact_hostname_and_applies_limit() -> None:
    with expect_single_query(
        f"GET services\nColumns: {_SERVICES_COLUMNS}\n"
        f"Filter: host_name = {_UNKNOWN_HOSTNAME}\n{_DEFAULT_ORDER_BY}\nLimit: 500",
    ) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        repo.fetch(
            _UNKNOWN_HOSTNAME,
            limit=500,
            query="",
            sorters=[],
            filters=ServiceFilter(""),
            fields=frozenset(),
        )


def test_fetch_without_limit_omits_limit_header() -> None:
    with expect_single_query(
        f"GET services\nColumns: {_SERVICES_COLUMNS}\n"
        f"Filter: host_name = {_UNKNOWN_HOSTNAME}\n{_DEFAULT_ORDER_BY}",
        match_type="ellipsis",
    ) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        repo.fetch(
            _UNKNOWN_HOSTNAME,
            limit=None,
            query="",
            sorters=[],
            filters=ServiceFilter(""),
            fields=frozenset(),
        )


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
            filters=ServiceFilter(""),
            fields=frozenset(),
        )


def test_fetch_filters_by_search_query_on_name_and_summary() -> None:
    with expect_single_query(
        f"GET services\nColumns: {_SERVICES_COLUMNS}\n"
        f"Filter: host_name = {_UNKNOWN_HOSTNAME}\n"
        "Filter: description ~~ CPU\nFilter: plugin_output ~~ CPU\nOr: 2\nAnd: 2\n"
        f"{_DEFAULT_ORDER_BY}",
        match_type="ellipsis",
    ) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        repo.fetch(
            _UNKNOWN_HOSTNAME,
            limit=None,
            query="CPU",
            sorters=[],
            filters=ServiceFilter(""),
            fields=frozenset(),
        )


def test_fetch_applies_filters() -> None:
    with expect_single_query(
        f"GET services\nColumns: {_SERVICES_COLUMNS}\n"
        f"Filter: host_name = {_UNKNOWN_HOSTNAME}\n"
        f"Filter: state = 1\n{_DEFAULT_ORDER_BY}",
        match_type="ellipsis",
    ) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        repo.fetch(
            _UNKNOWN_HOSTNAME,
            limit=None,
            query="",
            sorters=[],
            filters=ServiceFilter("Filter: state = 1"),
            fields=frozenset(),
        )


def test_fetch_reads_optional_columns_only_when_asked_for() -> None:
    with expect_single_query(
        f"GET services\nColumns: {_SERVICES_COLUMNS} labels label_sources tags\n"
        f"Filter: host_name = {_UNKNOWN_HOSTNAME}\n{_DEFAULT_ORDER_BY}",
        match_type="ellipsis",
    ) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        repo.fetch(
            _UNKNOWN_HOSTNAME,
            limit=None,
            query="",
            sorters=[],
            filters=ServiceFilter(""),
            fields=frozenset({ServiceOptionalField.LABELS, ServiceOptionalField.TAGS}),
        )


def test_count_matched_query_shape() -> None:
    with expect_single_query(
        f"GET services\nStats: state >= 0\n"
        f"Filter: host_name = {_UNKNOWN_HOSTNAME}\n"
        "Filter: description ~~ CPU\nFilter: plugin_output ~~ CPU\nOr: 2\nAnd: 2",
    ) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        assert repo.count_matched(_UNKNOWN_HOSTNAME, query="CPU", filters=ServiceFilter("")) == 0


def test_count_matched_applies_filters() -> None:
    with expect_single_query(
        f"GET services\nStats: state >= 0\n"
        f"Filter: host_name = {_UNKNOWN_HOSTNAME}\n"
        "Filter: state = 1",
    ) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        repo.count_matched(_UNKNOWN_HOSTNAME, query="", filters=ServiceFilter("Filter: state = 1"))


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
            "OrderBy: description asc natural",
            id="page default order",
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


def test_every_optional_field_names_the_columns_it_needs() -> None:
    """A new ServiceOptionalField must say which livestatus columns it reads."""
    assert set(_OPTIONAL_COLUMNS) == set(ServiceOptionalField)


def test_build_query_filter_without_a_query_matches_everything() -> None:
    assert _build_query_filter("").render() == []


def test_build_query_filter_searches_the_name_and_the_summary() -> None:
    assert _build_query_filter("CPU").render() == [
        ("Filter", "description ~~ CPU"),
        ("Filter", "plugin_output ~~ CPU"),
        ("Or", "2"),
    ]


@pytest.mark.parametrize(
    "staleness, threshold, expected_stale",
    [
        pytest.param(5.0, 3.5, True, id="staleness at or above the threshold is stale"),
        pytest.param(2.0, 3.5, False, id="staleness below the threshold is not stale"),
    ],
)
def test_fetch_derives_stale_from_the_staleness_threshold(
    staleness: float,
    threshold: float,
    expected_stale: bool,
    request_context: None,
    set_config: SetConfig,
) -> None:
    row = {
        "description": "CPU load",
        "host_name": _UNKNOWN_HOSTNAME,
        "state": 0,
        "plugin_output": "OK",
        "acknowledged": 0,
        "scheduled_downtime_depth": 0,
        "notifications_enabled": 1,
        "is_flapping": 0,
        "staleness": staleness,
        "last_check": 0,
        "last_state_change": 0,
        "perf_data": "",
        "check_command": "check_cpu",
    }
    with expect_single_query("GET services", tables={"services": [row]}) as live:
        repo = LiveStatusHostServicesRepository(connection=live)
        with set_config(staleness_threshold=threshold):
            services = repo.fetch(
                _UNKNOWN_HOSTNAME,
                limit=None,
                query="",
                sorters=[],
                filters=ServiceFilter(""),
                fields=frozenset(),
            )

    assert [service.stale for service in services] == [expected_stale]
