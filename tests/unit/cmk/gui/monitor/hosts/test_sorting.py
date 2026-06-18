#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from polyfactory.factories import DataclassFactory

from cmk.gui.monitor.hosts._models import Host, HostSort, HostSortColumn, HostSortDirection
from cmk.gui.monitor.hosts._sorting import host_sorter


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
