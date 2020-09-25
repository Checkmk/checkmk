#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from typing import Dict
import pytest  # type: ignore[import]
from testlib import get_value_store_fixture
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    Result,
    Service,
    State as state,
    type_defs,
)
from cmk.base.plugins.agent_based import lnx_if
from cmk.base.plugins.agent_based.utils import interfaces

value_store_fixture = get_value_store_fixture(interfaces)


@pytest.mark.parametrize('string_table, result', [
    (
        [
            [u'[start_iplink]'],
            [
                u'1:', u'wlp3s0:', u'<BROADCAST,MULTICAST>', u'mtu', u'1500', u'qdisc', u'fq_codel',
                u'state', u'UP', u'mode', u'DORMANT', u'group', u'default', u'qlen', u'1000'
            ],
            [u'link/ether', u'AA:AA:AA:AA:AA:AA', u'brd', u'BB:BB:BB:BB:BB:BB'],
            [u'[end_iplink]'],
            [u'wlp3s0', u'130923553 201184 0 0 0 0 0 16078 23586281 142684 0 0 0 0 0 0'],
        ],
        [
            '1', 'wlp3s0', 'wlp3s0', '6', 0, '2', 130923553, 217262, 16078, 0, 0, 0, 23586281,
            142684, 0, 0, 0, 0, 0, '\xaa\xaa\xaa\xaa\xaa\xaa'
        ],
    ),
    (
        [
            [u'[start_iplink]'],
            [
                u'1:', u'wlp3s0:', u'<BROADCAST,MULTICAST,UP>', u'mtu', u'1500', u'qdisc',
                u'fq_codel', u'state', u'UP', u'mode', u'DORMANT', u'group', u'default', u'qlen',
                u'1000'
            ],
            [u'link/ether', u'BB:BB:BB:BB:BB:BB', u'brd', u'BB:BB:BB:BB:BB:BB'],
            [u'[end_iplink]'],
            [u'wlp3s0', u'130923553 201184 0 0 0 0 0 16078 23586281 142684 0 0 0 0 0 0'],
        ],
        [
            '1', 'wlp3s0', 'wlp3s0', '6', 0, '1', 130923553, 217262, 16078, 0, 0, 0, 23586281,
            142684, 0, 0, 0, 0, 0, '\xbb\xbb\xbb\xbb\xbb\xbb'
        ],
    )
])
def test_parse_lnx_if(string_table, result):
    assert lnx_if.parse_lnx_if(string_table)[0][0] == interfaces.Interface(*result)


INTERFACE = interfaces.Interface('1', 'wlp3s0', 'wlp3s0', '6', 0, '1', 130923553, 217262, 16078, 0,
                                 0, 0, 23586281, 142684, 0, 0, 0, 0, 0, '\xaa\xaa\xaa\xaa\xaa\xaa')

PARAMS = type_defs.Parameters({
    'errors': (0.01, 0.1),
    'speed': 10000000,
    'traffic': [('both', ('upper', ('perc', (5.0, 20.0))))],
    'state': ['1'],
})


def test_check_lnx_if(monkeypatch, value_store):
    section_if = [INTERFACE]
    section: lnx_if.Section = (section_if, {})
    monkeypatch.setattr('time.time', lambda: 0)
    with pytest.raises(IgnoreResultsError):
        list(lnx_if.check_lnx_if(
            INTERFACE.index,
            PARAMS,
            section,
        ))
    monkeypatch.setattr('time.time', lambda: 1)
    result_lnx_if = list(lnx_if.check_lnx_if(
        INTERFACE.index,
        PARAMS,
        section,
    ))
    monkeypatch.setattr('time.time', lambda: 2)
    result_interfaces = list(
        interfaces.check_multiple_interfaces(
            INTERFACE.index,
            PARAMS,
            section_if,
        ))
    assert result_lnx_if == result_interfaces


def test_cluster_check_lnx_if(monkeypatch, value_store):
    section: Dict[str, lnx_if.Section] = {}
    ifaces = []
    for i in range(3):
        iface = copy.copy(INTERFACE)
        iface.node = 'node%s' % i
        ifaces_node = [iface] * (i + 1)
        section[iface.node] = ifaces_node, {}
        ifaces += ifaces_node
    monkeypatch.setattr('time.time', lambda: 0)
    with pytest.raises(IgnoreResultsError):
        list(lnx_if.cluster_check_lnx_if(
            INTERFACE.index,
            PARAMS,
            section,
        ))
    monkeypatch.setattr('time.time', lambda: 1)
    result_lnx_if = list(lnx_if.cluster_check_lnx_if(
        INTERFACE.index,
        PARAMS,
        section,
    ))
    monkeypatch.setattr('time.time', lambda: 2)
    result_interfaces = list(interfaces.check_multiple_interfaces(
        INTERFACE.index,
        PARAMS,
        ifaces,
    ))
    assert result_lnx_if == result_interfaces


@pytest.mark.parametrize('string_table, discovery_results, items_params_results', [
    (
        [
            [u'[start_iplink]'],
            [
                u'1:', u'lo:', u'<LOOPBACK,UP,LOWER_UP>', u'mtu', u'65536', u'qdisc', u'noqueue',
                u'state', u'UNKNOWN', u'mode', u'DEFAULT', u'group', u'default', u'qlen', u'1000'
            ],
            [u'link/loopback', u'00:00:00:00:00:00', u'brd', u'00:00:00:00:00:00'],
            [
                u'2:', u'wlp3s0:', u'<BROADCAST,MULTICAST,UP,LOWER_UP>', u'mtu', u'1500', u'qdisc',
                u'fq_codel', u'state', u'UP', u'mode', u'DORMANT', u'group', u'default', u'qlen',
                u'1000'
            ],
            [u'link/ether', u'AA:AA:AA:AA:AA:BB', u'brd', u'BB:BB:BB:BB:BB:BB'],
            [
                u'3:', u'docker0:', u'<BROADCAST,MULTICAST,UP,LOWER_UP>', u'mtu', u'1500', u'qdisc',
                u'noqueue', u'state', u'UP', u'mode', u'DEFAULT', u'group', u'default'
            ],
            [u'link/ether', u'AA:AA:AA:AA:AA:AA', u'brd', u'BB:BB:BB:BB:BB:BB'],
            [
                u'5:', u'veth6a06585@if4:', u'<BROADCAST,MULTICAST,UP,LOWER_UP>', u'mtu', u'1500',
                u'qdisc', u'noqueue', u'master', u'docker0', u'state', u'UP', u'mode', u'DEFAULT',
                u'group', u'default'
            ],
            [
                u'link/ether', u'AA:AA:AA:AA:AA:AA', u'brd', u'BB:BB:BB:BB:BB:BB', u'link-netnsid',
                u'0'
            ],
            [u'[end_iplink]'],
            [
                u'lo',
                u' 164379850  259656    0    0    0     0          0         0 164379850  259656    0    0    0     0       0          0'
            ],
            [
                u'wlp3s0',
                u' 130923553  201184    0    0    0     0          0     16078 23586281  142684    0    0    0     0       0          0'
            ],
            [
                u'docker0',
                u'       0       0    0    0    0     0          0         0    16250     184    0    0    0     0       0          0'
            ],
            [
                u'veth6a06585',
                u'       0       0    0    0    0     0          0         0    25963     287    0    0    0     0       0          0'
            ],
        ],
        [
            Service(item='1', parameters={
                'discovered_oper_status': ['1'],
                'discovered_speed': 0
            }),
            Service(item='4', parameters={
                'discovered_oper_status': ['1'],
                'discovered_speed': 0
            }),
        ],
        [
            (
                '1',
                {
                    'errors': (0.01, 0.1),
                    'speed': 0,
                    'state': ['1']
                },
                [
                    Result(state=state.OK, summary='[docker0]'),
                    Result(state=state.OK, summary='Operational state: up'),
                    Result(state=state.OK, summary='MAC: AA:AA:AA:AA:AA:AA'),
                    Result(state=state.OK, summary='speed unknown'),
                ],
            ),
            (
                '4',
                {
                    'errors': (0.01, 0.1),
                    'speed': 0,
                    'state': ['1']
                },
                [
                    Result(state=state.OK, summary='[wlp3s0]'),
                    Result(state=state.OK, summary='Operational state: up'),
                    Result(state=state.OK, summary='MAC: AA:AA:AA:AA:AA:BB'),
                    Result(state=state.OK, summary='speed unknown')
                ],
            ),
        ],
    ),
    (
        [
            [u'[start_iplink]'],
            [
                u'1:', u'lo:', u'<LOOPBACK,UP,LOWER_UP>', u'mtu', u'65536', u'qdisc', u'noqueue',
                u'state', u'UNKNOWN', u'mode', u'DEFAULT', u'group', u'default', u'qlen', u'1000'
            ],
            [u'link/loopback', u'00:00:00:00:00:00', u'brd', u'00:00:00:00:00:00'],
            [
                u'2:', u'wlp3s0:', u'<BROADCAST,MULTICAST,UP,LOWER_UP>', u'mtu', u'1500', u'qdisc',
                u'fq_codel', u'state', u'UP', u'mode', u'DORMANT', u'group', u'default', u'qlen',
                u'1000'
            ],
            [u'link/ether', u'AA:AA:AA:AA:AA:AA', u'brd', u'BB:BB:BB:BB:BB:BB'],
            [
                u'3:', u'docker0:', u'<BROADCAST,MULTICAST,UP,LOWER_UP>', u'mtu', u'1500', u'qdisc',
                u'noqueue', u'state', u'UP', u'mode', u'DEFAULT', u'group', u'default'
            ],
            [u'link/ether', u'AA:AA:AA:AA:AA:AA', u'brd', u'BB:BB:BB:BB:BB:BB'],
            [
                u'5:', u'veth6a06585@if4:', u'<BROADCAST,MULTICAST,UP,LOWER_UP>', u'mtu', u'1500',
                u'qdisc', u'noqueue', u'master', u'docker0', u'state', u'UP', u'mode', u'DEFAULT',
                u'group', u'default'
            ],
            [
                u'link/ether', u'AA:AA:AA:AA:AA:AA', u'brd', u'BB:BB:BB:BB:BB:BB', u'link-netnsid',
                u'0'
            ],
            [u'[end_iplink]'],
            [
                u'lo',
                u' 164379850  259656    0    0    0     0          0         0 164379850  259656    0    0    0     0       0          0'
            ],
            [
                u'wlp3s0',
                u' 130923553  201184    0    0    0     0          0     16078 23586281  142684    0    0    0     0       0          0'
            ],
            [
                u'docker0',
                u'       0       0    0    0    0     0          0         0    16250     184    0    0    0     0       0          0'
            ],
            [
                u'veth6a06585',
                u'       0       0    0    0    0     0          0         0    25963     287    0    0    0     0       0          0'
            ],
            [u'[lo]'],
            [u'Link detected', u' yes'],
            [u'Address', u' 00', u'00', u'00', u'00', u'00', u'00'],
            [u'[docker0]'],
            [u'Link detected', u' yes'],
            [u'Address', u' AA', u'AA', u'AA', u'AA', u'AA', u'AA'],
            [u'[veth6a06585]'],
            [u'Speed', u' 10000Mb/s'],
            [u'Duplex', u' Full'],
            [u'Auto-negotiation', u' off'],
            [u'Link detected', u' yes'],
            [u'Address', u' AA', u'AA', u'AA', u'AA', u'AA', u'AA'],
            [u'[wlp3s0]'],
            [u'Address', u' AA', u'AA', u'AA', u'AA', u'AA', u'AA'],
        ],
        [
            Service(item='2', parameters={
                'discovered_oper_status': ['1'],
                'discovered_speed': 0
            }),
            Service(item='4', parameters={
                'discovered_oper_status': ['1'],
                'discovered_speed': 0
            }),
        ],
        [
            (
                '2',
                {
                    'errors': (0.01, 0.1),
                    'speed': 0,
                    'state': ['1']
                },
                [
                    Result(state=state.OK, summary='[docker0]'),
                    Result(state=state.OK, summary='Operational state: up'),
                    Result(state=state.OK, summary='MAC: AA:AA:AA:AA:AA:AA'),
                    Result(state=state.OK, summary='speed unknown'),
                ],
            ),
            (
                '4',
                {
                    'errors': (0.01, 0.1),
                    'speed': 0,
                    'state': ['1']
                },
                [
                    Result(state=state.OK, summary='[wlp3s0]'),
                    Result(state=state.OK, summary='Operational state: up'),
                    Result(state=state.OK, summary='MAC: AA:AA:AA:AA:AA:AA'),
                    Result(state=state.OK, summary='speed unknown'),
                ],
            ),
        ],
    ),
    (
        [
            [u'[start_iplink]'],
            [
                u'1:', u'lo:', u'<LOOPBACK,UP,LOWER_UP>', u'mtu', u'65536', u'qdisc', u'noqueue',
                u'state', u'UNKNOWN', u'mode', u'DEFAULT', u'group', u'default', u'qlen', u'1000'
            ],
            [u'link/loopback', u'00:00:00:00:00:00', u'brd', u'00:00:00:00:00:00'],
            [
                u'2:', u'wlp3s0:', u'<BROADCAST,MULTICAST,UP,LOWER_UP>', u'mtu', u'1500', u'qdisc',
                u'fq_codel', u'state', u'UNKNOWN', u'mode', u'DORMANT', u'group', u'default',
                u'qlen', u'1000'
            ],
            [u'link/ether', u'AA:AA:AA:AA:AA:AA', u'brd', u'BB:BB:BB:BB:BB:BB'],
            [
                u'3:', u'docker0:', u'<BROADCAST,MULTICAST,UP,LOWER_UP>', u'mtu', u'1500', u'qdisc',
                u'noqueue', u'state', u'UNKNOWN', u'mode', u'DEFAULT', u'group', u'default'
            ],
            [u'link/ether', u'AA:AA:AA:AA:AA:AA', u'brd', u'BB:BB:BB:BB:BB:BB'],
            [
                u'5:', u'veth6a06585@if4:', u'<BROADCAST,MULTICAST,UP,LOWER_UP>', u'mtu', u'1500',
                u'qdisc', u'noqueue', u'master', u'docker0', u'state', u'UNKNOWN', u'mode',
                u'DEFAULT', u'group', u'default'
            ],
            [
                u'link/ether', u'AA:AA:AA:AA:AA:AA', u'brd', u'BB:BB:BB:BB:BB:BB', u'link-netnsid',
                u'0'
            ],
            [u'[end_iplink]'],
            [
                u'lo',
                u' 164379850  259656    0    0    0     0          0         0 164379850  259656    0    0    0     0       0          0'
            ],
            [
                u'wlp3s0',
                u' 130923553  201184    0    0    0     0          0     16078 23586281  142684    0    0    0     0       0          0'
            ],
            [
                u'docker0',
                u'       0       0    0    0    0     0          0         0    16250     184    0    0    0     0       0          0'
            ],
            [
                u'veth6a06585',
                u'       0       0    0    0    0     0          0         0    25963     287    0    0    0     0       0          0'
            ],
            [u'[lo]'],
            [u'Link detected', u' yes'],
            [u'Address', u' 00', u'00', u'00', u'00', u'00', u'00'],
            [u'[docker0]'],
            [u'Link detected', u' yes'],
            [u'Address', u' AA', u'AA', u'AA', u'AA', u'AA', u'AA'],
            [u'[veth6a06585]'],
            [u'Speed', u' 10000Mb/s'],
            [u'Duplex', u' Full'],
            [u'Auto-negotiation', u' off'],
            [u'Link detected', u' yes'],
            [u'Address', u' AA', u'AA', u'AA', u'AA', u'AA', u'AA'],
            [u'[wlp3s0]'],
            [u'Address', u' AA', u'AA', u'AA', u'AA', u'AA', u'AA'],
        ],
        [
            Service(item='2', parameters={
                'discovered_oper_status': ['1'],
                'discovered_speed': 0
            }),
            Service(item='4', parameters={
                'discovered_oper_status': ['1'],
                'discovered_speed': 0
            }),
        ],
        [
            (
                '2',
                {
                    'errors': (0.01, 0.1),
                    'speed': 0,
                    'state': ['1']
                },
                [
                    Result(state=state.OK, summary='[docker0]'),
                    Result(state=state.OK, summary='Operational state: up'),
                    Result(state=state.OK, summary='MAC: AA:AA:AA:AA:AA:AA'),
                    Result(state=state.OK, summary='speed unknown'),
                ],
            ),
            (
                '4',
                {
                    'errors': (0.01, 0.1),
                    'speed': 0,
                    'state': ['1']
                },
                [
                    Result(state=state.OK, summary='[wlp3s0]'),
                    Result(state=state.OK, summary='Operational state: up'),
                    Result(state=state.OK, summary='MAC: AA:AA:AA:AA:AA:AA'),
                    Result(state=state.OK, summary='speed unknown'),
                ],
            ),
        ],
    ),
    (
        [
            [u'em0', u'376716785370 417455222 0 0 0 0 0 0 383578105955 414581956 0 0 0 0 0 0'],
            [u'tun0', u'342545566242 0 259949262 0 0 0 0 0  0 19196 0 0  0 0'],
            [u'tun1', u'2422824602 0 2357563 0 0 0 0 0  0 0 0 0  0 0'],
            [u'[em0]'],
            [u'Speed', u' 1000Mb/s'],
            [u'Duplex', u' Full'],
            [u'Auto-negotiation', u' on'],
            [u'Link detected', u' yes'],
            [u'Address', u' 00', u'AA', u'11', u'BB', u'22', u'CC'],
            [u'[tun0]'],
            [u'Link detected', u' yes'],
            [u'Address', u' 123'],
            [u'[tun1]'],
            [u'Link detected', u' yes'],
            [u'Address', u' 456'],
        ],
        [
            Service(item='1',
                    parameters={
                        'discovered_oper_status': ['1'],
                        'discovered_speed': 1000000000
                    }),
            Service(item='2', parameters={
                'discovered_oper_status': ['1'],
                'discovered_speed': 0
            }),
            Service(item='3', parameters={
                'discovered_oper_status': ['1'],
                'discovered_speed': 0
            }),
        ],
        [
            (
                '1',
                {
                    'errors': (0.01, 0.1),
                    'speed': 1000000000,
                    'state': ['1']
                },
                [
                    Result(state=state.OK, summary='[em0]'),
                    Result(state=state.OK, summary='Operational state: up'),
                    Result(state=state.OK, summary='MAC: 00:AA:11:BB:22:CC'),
                    Result(state=state.OK, summary='1 GBit/s'),
                ],
            ),
            (
                '2',
                {
                    'errors': (0.01, 0.1),
                    'speed': 0,
                    'state': ['1']
                },
                [
                    Result(state=state.OK, summary='[tun0]'),
                    Result(state=state.OK, summary='Operational state: up'),
                    Result(state=state.OK, summary='speed unknown'),
                ],
            ),
            (
                '3',
                {
                    'errors': (0.01, 0.1),
                    'speed': 0,
                    'state': ['1']
                },
                [
                    Result(state=state.OK, summary='[tun1]'),
                    Result(state=state.OK, summary='Operational state: up'),
                    Result(state=state.OK, summary='speed unknown'),
                ],
            ),
        ],
    ),
])
def test_lnx_if_regression(
    monkeypatch,
    string_table,
    discovery_results,
    items_params_results,
):
    section = lnx_if.parse_lnx_if(string_table)

    assert list(
        lnx_if.discover_lnx_if(
            [type_defs.Parameters(interfaces.DISCOVERY_DEFAULT_PARAMETERS)],
            section,
        )) == discovery_results

    monkeypatch.setattr(interfaces, 'get_value_store', lambda: {})
    for item, par, res in items_params_results:
        assert list(lnx_if.check_lnx_if(
            item,
            type_defs.Parameters(par),
            section,
        )) == res

    node_name = 'node'
    for item, par, res in items_params_results:
        assert list(
            lnx_if.cluster_check_lnx_if(
                item,
                type_defs.Parameters(par),
                {node_name: section},
            )) == [
                Result(
                    state=res[0].state,
                    summary=res[0].summary + ' on %s' % node_name,
                ),
            ] + res[1:]
