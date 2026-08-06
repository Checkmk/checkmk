#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
import functools

import pytest

from cmk.gui.monitor.services._models import (
    ServiceSort,
    ServiceSortColumn,
    ServiceSortDirection,
    ServiceState,
)
from cmk.gui.monitor.services._sorting import service_sorter, sort_naturally

from .testlib import ServiceFactory


def test_no_sorting() -> None:
    services = [
        ServiceFactory.build(name="banana"),
        ServiceFactory.build(name="chocolate"),
        ServiceFactory.build(name="apple"),
    ]

    value = [service.name for service in sorted(services, key=service_sorter([]))]
    expected = [
        "banana",
        "chocolate",
        "apple",
    ]

    assert value == expected


def test_single_column_sorting() -> None:
    services = [
        ServiceFactory.build(name="banana"),
        ServiceFactory.build(name="chocolate"),
        ServiceFactory.build(name="apple"),
    ]
    sorters = [ServiceSort(column=ServiceSortColumn.NAME, direction=ServiceSortDirection.ASC)]

    value = [service.name for service in sorted(services, key=service_sorter(sorters))]
    expected = [
        "apple",
        "banana",
        "chocolate",
    ]

    assert value == expected


def test_descending_sorting() -> None:
    services = [
        ServiceFactory.build(state=ServiceState.WARN),
        ServiceFactory.build(state=ServiceState.CRIT),
        ServiceFactory.build(state=ServiceState.OK),
    ]
    sorters = [ServiceSort(column=ServiceSortColumn.STATE, direction=ServiceSortDirection.DESC)]

    value = [service.state for service in sorted(services, key=service_sorter(sorters))]
    expected = [
        ServiceState.CRIT,
        ServiceState.WARN,
        ServiceState.OK,
    ]

    assert value == expected


def test_multi_column_sorting() -> None:
    services = [
        ServiceFactory.build(state=ServiceState.OK, name="CPU load"),
        ServiceFactory.build(state=ServiceState.CRIT, name="Memory"),
        ServiceFactory.build(state=ServiceState.OK, name="Check_MK"),
    ]
    sorters = [
        ServiceSort(column=ServiceSortColumn.STATE, direction=ServiceSortDirection.DESC),
        ServiceSort(column=ServiceSortColumn.NAME, direction=ServiceSortDirection.ASC),
    ]

    value = [
        (service.state, service.name) for service in sorted(services, key=service_sorter(sorters))
    ]
    expected = [
        (ServiceState.CRIT, "Memory"),
        (ServiceState.OK, "Check_MK"),
        (ServiceState.OK, "CPU load"),
    ]

    assert value == expected


def test_service_sorter_timestamp_columns() -> None:
    services = [
        ServiceFactory.build(last_check=dt.datetime(2026, 1, 3, tzinfo=dt.UTC)),
        ServiceFactory.build(last_check=dt.datetime(2026, 1, 1, tzinfo=dt.UTC)),
        ServiceFactory.build(last_check=dt.datetime(2026, 1, 2, tzinfo=dt.UTC)),
    ]
    sorters = [ServiceSort(column=ServiceSortColumn.LAST_CHECK, direction=ServiceSortDirection.ASC)]

    value = [service.last_check for service in sorted(services, key=service_sorter(sorters))]
    expected = [
        dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        dt.datetime(2026, 1, 2, tzinfo=dt.UTC),
        dt.datetime(2026, 1, 3, tzinfo=dt.UTC),
    ]

    assert value == expected


def test_service_sorter_sorts_never_checked_services_first() -> None:
    services = [
        ServiceFactory.build(last_check=dt.datetime(2026, 1, 2, tzinfo=dt.UTC)),
        ServiceFactory.build(last_check=None),
        ServiceFactory.build(last_check=dt.datetime(2026, 1, 1, tzinfo=dt.UTC)),
    ]
    sorters = [ServiceSort(column=ServiceSortColumn.LAST_CHECK, direction=ServiceSortDirection.ASC)]

    value = [service.last_check for service in sorted(services, key=service_sorter(sorters))]
    expected = [
        None,
        dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        dt.datetime(2026, 1, 2, tzinfo=dt.UTC),
    ]

    assert value == expected


@pytest.mark.parametrize(
    "column, attribute",
    [
        pytest.param(ServiceSortColumn.NAME, "name", id="name"),
        pytest.param(ServiceSortColumn.SUMMARY, "summary", id="summary"),
    ],
)
def test_service_sorter_uses_natural_sort_for_string_columns(
    column: ServiceSortColumn, attribute: str
) -> None:
    services = [
        ServiceFactory.build(**{attribute: "Interface 10"}),
        ServiceFactory.build(**{attribute: "interface 2"}),
        ServiceFactory.build(**{attribute: "Interface 1"}),
    ]
    sorters = [ServiceSort(column=column, direction=ServiceSortDirection.ASC)]

    value = [
        getattr(service, attribute) for service in sorted(services, key=service_sorter(sorters))
    ]
    expected = [
        "Interface 1",
        "interface 2",
        "Interface 10",
    ]

    assert value == expected


@pytest.mark.parametrize(
    "a, b",
    [
        ("", ""),
        ("CPU load", "CPU load"),
        ("7", "007"),
        ("Interface 07", "Interface 7"),
    ],
)
def test_sort_naturally_equal(a: str, b: str) -> None:
    assert sort_naturally(a, b) == 0
    assert sort_naturally(b, a) == 0


@pytest.mark.parametrize(
    "a, b",
    [
        ("apple", "banana"),
        ("ab", "abc"),
        ("Interface 2", "Interface 10"),
        ("9", "10"),
        ("Interface 007x", "Interface 7y"),
        ("ab1", "abc"),
        ("Interface", "interface"),
        ("INTERFACE 10", "interface 10"),
    ],
)
def test_sort_naturally_string_number_combinations(a: str, b: str) -> None:
    assert sort_naturally(a, b) < 0
    assert sort_naturally(b, a) > 0


def test_sort_naturally_sorts_service_names_correctly() -> None:
    names = [
        "Interface 10",
        "Interface 2",
        "Check_MK",
        "Interface 1/0/10",
        "Interface 1/0/2",
        "CPU load",
        "Filesystem /var",
        "Filesystem /",
    ]

    value = sorted(names, key=functools.cmp_to_key(sort_naturally))
    expected = [
        "Check_MK",
        "CPU load",
        "Filesystem /",
        "Filesystem /var",
        "Interface 1/0/2",
        "Interface 1/0/10",
        "Interface 2",
        "Interface 10",
    ]

    assert value == expected
