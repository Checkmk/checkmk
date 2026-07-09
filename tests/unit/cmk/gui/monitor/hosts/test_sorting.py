#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools

import pytest
from polyfactory.factories import DataclassFactory

from cmk.gui.monitor.hosts._models import Host, HostSort, HostSortColumn, HostSortDirection
from cmk.gui.monitor.hosts._sorting import host_sorter, sort_naturally


class HostFactory(DataclassFactory[Host]):
    __check_model__ = False


def test_no_sorting() -> None:
    hosts = [
        HostFactory.build(name="banana"),
        HostFactory.build(name="chocolate"),
        HostFactory.build(name="apple"),
    ]

    value = [host.name for host in sorted(hosts, key=host_sorter([]))]
    expected = [
        "banana",
        "chocolate",
        "apple",
    ]

    assert value == expected


def test_single_column_sorting() -> None:
    hosts = [
        HostFactory.build(name="banana"),
        HostFactory.build(name="chocolate"),
        HostFactory.build(name="apple"),
    ]
    sorters = [HostSort(column=HostSortColumn.NAME, direction=HostSortDirection.ASC)]

    value = [host.name for host in sorted(hosts, key=host_sorter(sorters))]
    expected = [
        "apple",
        "banana",
        "chocolate",
    ]

    assert value == expected


def test_multi_column_sorting() -> None:
    hosts = [
        HostFactory.build(address="127.0.0.1", service_counts={"total": 5}),
        HostFactory.build(address="127.0.0.2", service_counts={"total": 10}),
        HostFactory.build(address="127.0.0.1", service_counts={"total": 15}),
    ]
    sorters = [
        HostSort(column=HostSortColumn.ADDRESS, direction=HostSortDirection.ASC),
        HostSort(column=HostSortColumn.NUM_SERVICES, direction=HostSortDirection.DESC),
    ]

    value = [
        (host.address, host.service_counts.total)
        for host in sorted(hosts, key=host_sorter(sorters))
    ]
    expected = [
        ("127.0.0.1", 15),
        ("127.0.0.1", 5),
        ("127.0.0.2", 10),
    ]

    assert value == expected


def test_host_sorter_uses_natural_sort_for_string_columns() -> None:
    hosts = [
        HostFactory.build(name="host10"),
        HostFactory.build(name="Host2"),
        HostFactory.build(name="host1"),
    ]
    sorters = [HostSort(column=HostSortColumn.NAME, direction=HostSortDirection.ASC)]

    value = [host.name for host in sorted(hosts, key=host_sorter(sorters))]
    expected = [
        "host1",
        "Host2",
        "host10",
    ]

    assert value == expected


@pytest.mark.parametrize(
    "a, b",
    [
        ("", ""),
        ("host1", "host1"),
        ("7", "007"),
        ("host07", "host7"),
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
        ("host2", "host10"),
        ("9", "10"),
        ("host007x", "host7y"),
        ("ab1", "abc"),
        ("Host", "host"),
        ("HOST10", "host10"),
    ],
)
def test_sort_naturally_string_number_combinations(a: str, b: str) -> None:
    assert sort_naturally(a, b) < 0
    assert sort_naturally(b, a) > 0


@pytest.mark.parametrize(
    "a, b",
    [
        pytest.param("2.1.1.1", "10.1.1.1", id="first item"),
        pytest.param("1.2.1.1", "1.10.1.1", id="second item"),
        pytest.param("1.1.2.1", "1.1.10.1", id="third item"),
        pytest.param("1.1.1.2", "1.1.1.10", id="fourth item"),
    ],
)
def test_sort_naturally_ipv4_addresses(a: str, b: str) -> None:
    assert sort_naturally(a, b) < 0
    assert sort_naturally(b, a) > 0


def test_sort_naturally_ipv6_uncompressed() -> None:
    addresses = [
        "fe80:0000:0000:0000:0000:0000:0000:0001",
        "2001:0db8:0000:0000:0000:0000:0000:0001",
        "0000:0000:0000:0000:0000:ffff:c0a8:0101",
        "0000:0000:0000:0000:0000:0000:0000:0001",
        "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
    ]

    value = sorted(addresses, key=functools.cmp_to_key(sort_naturally))
    expected = [
        "0000:0000:0000:0000:0000:0000:0000:0001",
        "0000:0000:0000:0000:0000:ffff:c0a8:0101",
        "2001:0db8:0000:0000:0000:0000:0000:0001",
        "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        "fe80:0000:0000:0000:0000:0000:0000:0001",
    ]

    assert value == expected


# TODO: look into having a dedicated sort modifier for ipv6 in livestatus core. We can live with
# this for now. In order for this to work, we would want to normalize the address to uncompressed
# version and then pass that value to the natural sorting (works above).
@pytest.mark.xfail(strict=True, reason="Natural sort doesn't support ipv6 compressed")
def test_sort_naturally_ipv6_compressed() -> None:
    addresses = [
        "fe80::1",
        "2001:db8::1",
        "::ffff:192.168.1.1",
        "::1",
        "2001:db8:85a3::8a2e:370:7334",
    ]

    value = sorted(addresses, key=functools.cmp_to_key(sort_naturally))
    expected = [
        "::1",
        "::ffff:192.168.1.1",
        "2001:db8::1",
        "2001:db8:85a3::8a2e:370:7334",
        "fe80::1",
    ]

    assert value == expected


def test_sort_naturally_sorts_numbers_correctly() -> None:
    hosts = ["host10", "Host2", "host1", "host20", "host3", "HOST10"]

    value = sorted(hosts, key=functools.cmp_to_key(sort_naturally))
    expected = [
        "host1",
        "Host2",
        "host3",
        "HOST10",
        "host10",
        "host20",
    ]

    assert value == expected
