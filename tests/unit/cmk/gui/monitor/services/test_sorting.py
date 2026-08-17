#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools

import pytest

from cmk.gui.monitor.services._models import (
    ServiceSort,
    ServiceSortColumn,
    ServiceSortDirection,
    ServiceState,
)
from cmk.gui.monitor.services._sorting import (
    _SERVICE_NAME_RANKS,
    service_sorter,
    sort_naturally,
)
from cmk.gui.view_utils import cmp_service_name_equiv

from .testlib import ServiceFactory


def test_requesting_no_sorter_applies_the_page_default() -> None:
    """An empty sorter list means the page default, which sorts by name."""
    services = [
        ServiceFactory.build(name="banana"),
        ServiceFactory.build(name="chocolate"),
        ServiceFactory.build(name="apple"),
    ]

    value = [service.name for service in sorted(services, key=service_sorter([]))]
    expected = [
        "apple",
        "banana",
        "chocolate",
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
        ServiceFactory.build(last_check=1767398400),
        ServiceFactory.build(last_check=1767225600),
        ServiceFactory.build(last_check=1767312000),
    ]
    sorters = [ServiceSort(column=ServiceSortColumn.LAST_CHECK, direction=ServiceSortDirection.ASC)]

    value = [service.last_check for service in sorted(services, key=service_sorter(sorters))]
    expected = [
        1767225600,
        1767312000,
        1767398400,
    ]

    assert value == expected


def test_service_sorter_sorts_never_checked_services_first() -> None:
    services = [
        ServiceFactory.build(last_check=1767312000),
        ServiceFactory.build(last_check=None),
        ServiceFactory.build(last_check=1767225600),
    ]
    sorters = [ServiceSort(column=ServiceSortColumn.LAST_CHECK, direction=ServiceSortDirection.ASC)]

    value = [service.last_check for service in sorted(services, key=service_sorter(sorters))]
    expected = [
        None,
        1767225600,
        1767312000,
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


_PRIORITIZED_NAMES = [
    "Check_MK",
    "Check_MK Agent",
    "Check_MK Discovery",
    "Check_MK inventory",
    "Check_MK HW/SW Inventory",
]

# Deliberately shuffled, and picked so that a plain natural sort disagrees twice over: "APT Updates"
# would lead, and "Check_MK HW/SW Inventory" would precede "Check_MK inventory" ("h" < "i").
_MIXED_NAMES = [
    "Check_MK HW/SW Inventory",
    "CPU load",
    "Check_MK inventory",
    "APT Updates",
    "Check_MK",
    "Check_MK Discovery",
    "Check_MK Agent",
    "Interface 2",
    "Interface 10",
]

_UNPRIORITIZED_NAMES = ["APT Updates", "CPU load", "Interface 2", "Interface 10"]


def test_check_mk_services_sort_before_everything_else_in_the_default_order() -> None:
    services = [ServiceFactory.build(name=name) for name in _MIXED_NAMES]

    value = [service.name for service in sorted(services, key=service_sorter([]))]

    assert value == [*_PRIORITIZED_NAMES, *_UNPRIORITIZED_NAMES]


def test_an_explicitly_requested_name_sort_does_not_prioritize_check_mk_services() -> None:
    """The priority belongs to the default order only; a requested sort is taken literally."""
    services = [ServiceFactory.build(name=name) for name in _MIXED_NAMES]
    sorters = [ServiceSort(column=ServiceSortColumn.NAME, direction=ServiceSortDirection.ASC)]

    value = [service.name for service in sorted(services, key=service_sorter(sorters))]

    assert value == sorted(_MIXED_NAMES, key=functools.cmp_to_key(sort_naturally))
    # The discriminating pair: natural sort leads with "APT Updates", the default order does not.
    assert value[0] == "APT Updates"


def test_descending_name_sort_is_a_plain_reverse_natural_sort() -> None:
    services = [ServiceFactory.build(name=name) for name in _MIXED_NAMES]
    sorters = [ServiceSort(column=ServiceSortColumn.NAME, direction=ServiceSortDirection.DESC)]

    value = [service.name for service in sorted(services, key=service_sorter(sorters))]

    assert value == sorted(_MIXED_NAMES, key=functools.cmp_to_key(sort_naturally), reverse=True)


def test_check_mk_priority_does_not_apply_to_a_secondary_name_sort() -> None:
    services = [
        ServiceFactory.build(state=ServiceState.OK, name="Check_MK"),
        ServiceFactory.build(state=ServiceState.OK, name="APT Updates"),
        ServiceFactory.build(state=ServiceState.CRIT, name="Memory"),
    ]
    sorters = [
        ServiceSort(column=ServiceSortColumn.STATE, direction=ServiceSortDirection.DESC),
        ServiceSort(column=ServiceSortColumn.NAME, direction=ServiceSortDirection.ASC),
    ]

    value = [
        (service.state, service.name) for service in sorted(services, key=service_sorter(sorters))
    ]

    assert value == [
        (ServiceState.CRIT, "Memory"),
        (ServiceState.OK, "APT Updates"),
        (ServiceState.OK, "Check_MK"),
    ]


@pytest.mark.parametrize(
    "near_miss",
    [
        pytest.param("check_mk", id="wrong case"),
        pytest.param("Check_MK Agent Deployment", id="longer name"),
        pytest.param("Check_MK HW/SW inventory", id="wrong case in suffix"),
        pytest.param("Check_MK Discovery ", id="trailing space"),
    ],
)
def test_only_exact_service_names_are_prioritized(near_miss: str) -> None:
    services = [
        ServiceFactory.build(name=near_miss),
        ServiceFactory.build(name="AAA"),
    ]

    value = [service.name for service in sorted(services, key=service_sorter([]))]

    assert value == ["AAA", near_miss]


def test_service_name_priority_does_not_affect_the_summary_sort() -> None:
    services = [
        ServiceFactory.build(name="Check_MK", summary="zzz"),
        ServiceFactory.build(name="APT Updates", summary="aaa"),
    ]
    sorters = [ServiceSort(column=ServiceSortColumn.SUMMARY, direction=ServiceSortDirection.ASC)]

    value = [service.summary for service in sorted(services, key=service_sorter(sorters))]

    assert value == ["aaa", "zzz"]


def test_service_name_ranks_match_the_legacy_sorter() -> None:
    """Guard our copy of the legacy ranking against drift on either side."""
    ours = sorted(_SERVICE_NAME_RANKS, key=_SERVICE_NAME_RANKS.__getitem__)

    assert ours == _PRIORITIZED_NAMES
    # cmp_service_name_equiv ranks anything it does not know last, so a stable sort by it has to
    # reproduce our order with the unknown name at the end.
    assert sorted([*ours, "APT Updates"], key=cmp_service_name_equiv) == [*ours, "APT Updates"]


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
