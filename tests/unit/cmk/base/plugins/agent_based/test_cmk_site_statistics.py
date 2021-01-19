#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.cmk_site_statistics import (
    HostStatistics,
    ServiceStatistics,
    check_cmk_site_statistics,
    discover_cmk_site_statistics,
    parse_cmk_site_statistics,
)
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Metric,
    Result,
    Service,
    State,
)

_SECTION = {
    'heute': (
        HostStatistics(up=1, down=0, unreachable=0, in_downtime=0),
        ServiceStatistics(ok=32, in_downtime=0, on_down_hosts=0, warning=2, unknown=0, critical=1),
    ),
    'gestern': (
        HostStatistics(up=1, down=2, unreachable=3, in_downtime=4),
        ServiceStatistics(ok=5, in_downtime=6, on_down_hosts=7, warning=8, unknown=9, critical=10),
    ),
}


def test_parse_cmk_site_statistics():
    assert parse_cmk_site_statistics([
        ['[heute]'],
        ['1', '0', '0', '0'],
        ['32', '0', '0', '2', '0', '1'],
        ['[gestern]'],
        ['1', '2', '3', '4'],
        ['5', '6', '7', '8', '9', '10'],
    ]) == _SECTION


def test_discover_cmk_site_statistics():
    assert list(discover_cmk_site_statistics(_SECTION)) == [
        Service(item='heute'),
        Service(item='gestern'),
    ]


def test_check_cmk_site_statistics():
    assert list(check_cmk_site_statistics('gestern', _SECTION)) == [
        Result(
            state=State.OK,
            summary='Total hosts: 10',
        ),
        Result(
            state=State.OK,
            summary='Problem hosts: 9',
            details='UP hosts: 1\nDOWN hosts: 2\nUnreachable hosts: 3\nHosts in downtime: 4',
        ),
        Result(
            state=State.OK,
            summary='Total services: 45',
        ),
        Result(
            state=State.OK,
            summary='Problem services: 40',
            details=
            'Services in downtime: 6\nServices of down hosts: 7\nWARNING services: 8\nUNKNOWN services: 9\nCRITICAL services: 10',
        ),
        Metric('cmk_hosts_up', 1.0),
        Metric('cmk_hosts_down', 2.0),
        Metric('cmk_hosts_unreachable', 3.0),
        Metric('cmk_hosts_in_downtime', 4.0),
        Metric('cmk_services_ok', 5.0),
        Metric('cmk_services_in_downtime', 6.0),
        Metric('cmk_services_on_down_hosts', 7.0),
        Metric('cmk_services_warning', 8.0),
        Metric('cmk_services_unknown', 9.0),
        Metric('cmk_services_critical', 10.0),
    ]
