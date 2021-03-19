#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.cisco_wlc import (
    parse_cisco_wlc,
    discovery_cisco_wlc,
    check_cisco_wlc,
    cluster_check_cisco_wlc,
)
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Result,
    Service,
    State as state,
)


@pytest.mark.parametrize("string_table,expected_parsed_data", [
    ([[['AP19', '1'], ['AP02', '1']]], {
        'AP19': '1',
        'AP02': '1'
    }),
])
def test_parse_cisco_wlc(string_table, expected_parsed_data):
    assert parse_cisco_wlc(string_table) == expected_parsed_data


@pytest.mark.parametrize("section,services", [
    ({
        'AP19': '1',
        'AP02': '1'
    }, [
        Service(item='AP19'),
        Service(item='AP02'),
    ]),
])
def test_discovery_cisco_wlc(section, services):
    assert list(discovery_cisco_wlc(section)) == services


@pytest.mark.parametrize("item,params,section,results", [
    ("AP19", {}, {
        'AP19': '1',
        'AP02': '1'
    }, [Result(state=state.OK, summary='Accesspoint: online')]),
    ("AP18", {}, {
        'AP19': '1',
        'AP02': '1'
    }, [Result(state=state.CRIT, summary='Accesspoint not found')]),
])
def test_check_cisco_wlc(item, params, section, results):
    assert list(check_cisco_wlc(item, params, section)) == results


@pytest.mark.parametrize("item,params,section,result", [
    ("AP19", {}, {
        "node1": {
            'AP19': '1',
            'AP02': '1'
        }
    }, [Result(state=state.OK, summary='Accesspoint: online (connected to node1)')]),
    ("AP18", {}, {
        "node1": {
            'AP19': '1',
            'AP02': '1'
        }
    }, [Result(state=state.CRIT, summary='Accesspoint not found')]),
])
def test_cluster_check_cisco_wlc(item, params, section, result):
    assert list(cluster_check_cisco_wlc(item, params, section)) == result
