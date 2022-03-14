#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
from typing import Any, Dict

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state  # type: ignore[import]
from cmk.base.plugins.agent_based.juniper_trpz_aps import (
    check_juniper_trpz_aps,
    cluster_check_juniper_trpz_aps,
    parse_juniper_trpz_aps,
)
from cmk.base.plugins.agent_based.juniper_trpz_aps_sessions import (
    _check_common_juniper_trpz_aps_sessions,
    discovery_juniper_trpz_aps_sessions,
    parse_juniper_trpz_aps_sessions,
)

NODE_SECTIONS = {
    "node1": [[
        ['12.109.103.48.50.49.50.48.51.48.50.54.50', '7', 'ap1'],
        ['12.109.103.48.50.49.50.48.51.51.56.49.53', '10', 'ap2'],
        ['12.109.103.48.50.49.50.48.51.52.53.50.56', '10', 'ap3'],
    ], [
        ['12.109.103.48.50.49.50.48.51.48.50.54.50.1', '24690029', '16204801769', '651256841', '167276559562', '504451972', '50496155159', '912917', '781', '3611152', '', ''],
        ['12.109.103.48.50.49.50.48.51.48.50.54.50.2', '54719444', '54400648964', '641366904', '158742162014', '121823862', '39011377605', '5533065', '185', '8081876', '', ''],
        ['12.109.103.48.50.49.50.48.51.51.56.49.53.1', '0', '0', '0', '0', '0', '0', '0', '0', '0', '', ''],
        ['12.109.103.48.50.49.50.48.51.51.56.49.53.2', '0', '0', '0', '0', '0', '0', '0', '0', '0', '', ''],
        ['12.109.103.48.50.49.50.48.51.52.53.50.56.1', '0', '0', '0', '0', '0', '0', '0', '0', '0', '', ''],
        ['12.109.103.48.50.49.50.48.51.52.53.50.56.2', '0', '0', '0', '0', '0', '0', '0', '0', '0', '', ''],
        ]],
    "node2": [[
        ['12.109.103.48.50.49.49.52.55.49.50.56.54', '10', 'ap4'],
        ['12.109.103.48.50.49.50.48.51.48.50.54.50', '10', 'ap1'],
        ['12.109.103.48.50.49.50.48.51.52.48.49.53', '7', 'ap5'],
        ['12.109.103.48.50.49.50.48.51.52.50.53.50', '10', 'ap6'],
        ['12.109.103.48.50.49.50.48.51.52.53.50.56', '7', 'ap3'],
    ], [
        ['12.109.103.48.50.49.49.52.55.49.50.56.54.1', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0' ],
        ['12.109.103.48.50.49.49.52.55.49.50.56.54.2', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0'],
        ['12.109.103.48.50.49.50.48.51.48.50.54.50.1', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0'],
        ['12.109.103.48.50.49.50.48.51.48.50.54.50.2', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0'],
        ['12.109.103.48.50.49.50.48.51.52.48.49.53.1', '7149592', '7336880399', '251847840', '55873545913', '25979034', '2903106704', '303976', '89', '1217100', '0', '-105'],
        ['12.109.103.48.50.49.50.48.51.52.48.49.53.2', '1565799', '1376818772', '175270265', '46544002662', '21691735', '1583881098', '48372', '44', '487952', '0', '-113'],
        ['12.109.103.48.50.49.50.48.51.52.50.53.50.1', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0'],
        ['12.109.103.48.50.49.50.48.51.52.50.53.50.2', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0'],
        ['12.109.103.48.50.49.50.48.51.52.53.50.56.1', '4848049', '3212600848', '719829578', '220915185448', '58949996', '4031986193', '115950', '29648', '280469', '0', '-113'],
        ['12.109.103.48.50.49.50.48.51.52.53.50.56.2', '28967139', '32227111122', '1311464430', '264567139422', '33356314', '24174473231', '1260767', '162', '1426963', '1', '-113'],
        ]],
    "node3": [[
        ['12.109.103.48.50.49.49.52.55.49.50.56.54', '7', 'ap4'],
        ['12.109.103.48.50.49.50.48.51.51.56.49.53', '7', 'ap2'],
        ['12.109.103.48.50.49.50.48.51.52.48.49.53', '10', 'ap5'],
        ['12.109.103.48.50.49.50.48.51.52.50.53.50', '7', 'ap6'],
    ], [
        ['12.109.103.48.50.49.49.52.55.49.50.56.54.1', '76919471', '88482655078', '1151204142', '228528823812', '356634591', '37901984374', '5124290', '992', '22365546', '0', '-102'],
        ['12.109.103.48.50.49.49.52.55.49.50.56.54.2', '5723407', '4034978261', '647754388', '174023660137', '87499187', '7415874135', '461152', '173', '1433566', '0', '-115'],
        ['12.109.103.48.50.49.50.48.51.51.56.49.53.1', '46465371', '37306814965', '765295951', '193391950676', '70864936', '7263478701', '1737022', '975', '6706667', '0', '-102'],
        ['12.109.103.48.50.49.50.48.51.51.56.49.53.2', '34490476', '30642026963', '738087688', '182084036827', '87719129', '17243618794', '3398924', '196', '5457109', '0', '-114'],
        ['12.109.103.48.50.49.50.48.51.52.48.49.53.1', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0'],
        ['12.109.103.48.50.49.50.48.51.52.48.49.53.2', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0'],
        ['12.109.103.48.50.49.50.48.51.52.50.53.50.1', '36144385', '38112823418', '1068977437', '220686191228', '582176451', '62550067378', '1396625', '463', '7581856', '0', '-103'],
        ['12.109.103.48.50.49.50.48.51.52.50.53.50.2', '9662814', '10893657649', '648933806', '174234350979', '83729153', '6702036409', '558807', '171', '1662070', '0', '-118'],
        ]],
}

PARSED_DATA = {
    'node1': ({
        'ap1': {'oid': '12.109.103.48.50.49.50.48.51.48.50.54.50', 'status': '7'},
        'ap2': {'oid': '12.109.103.48.50.49.50.48.51.51.56.49.53', 'status': '10'},
        'ap3': {'oid': '12.109.103.48.50.49.50.48.51.52.53.50.56', 'status': '10'},
        }, {
        '12.109.103.48.50.49.50.48.51.48.50.54.50': {
            '1': ([24690029, 16204801769, 651256841, 167276559562, 504451972, 50496155159, 912917, 781, 3611152],
                  0, 0),
            '2': ([54719444, 54400648964, 641366904, 158742162014, 121823862, 39011377605, 5533065, 185, 8081876], 0, 0)
        },
        '12.109.103.48.50.49.50.48.51.51.56.49.53': {
            '1': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0),
            '2': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0)
        },
        '12.109.103.48.50.49.50.48.51.52.53.50.56': {
            '1': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0),
            '2': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0)
        }
    }),
    'node2': ({
        'ap1': {'oid': '12.109.103.48.50.49.50.48.51.48.50.54.50', 'status': '10'},
        'ap3': {'oid': '12.109.103.48.50.49.50.48.51.52.53.50.56', 'status': '7'},
        'ap4': {'oid': '12.109.103.48.50.49.49.52.55.49.50.56.54', 'status': '10'},
        'ap5': {'oid': '12.109.103.48.50.49.50.48.51.52.48.49.53', 'status': '7'},
        'ap6': {'oid': '12.109.103.48.50.49.50.48.51.52.50.53.50', 'status': '10'}
    }, {
        '12.109.103.48.50.49.49.52.55.49.50.56.54': {
            '1': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0),
            '2': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0)
        },
        '12.109.103.48.50.49.50.48.51.48.50.54.50': {
            '1': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0),
            '2': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0)
        },
        '12.109.103.48.50.49.50.48.51.52.48.49.53': {
            '1': ([7149592, 7336880399, 251847840, 55873545913, 25979034, 2903106704, 303976, 89, 1217100],
                  0, -105),
            '2': ([1565799, 1376818772, 175270265, 46544002662, 21691735, 1583881098, 48372, 44, 487952],
                  0, -113)
        },
        '12.109.103.48.50.49.50.48.51.52.50.53.50': {
            '1': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0),
            '2': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0)
        },
        '12.109.103.48.50.49.50.48.51.52.53.50.56': {
            '1': ([4848049, 3212600848, 719829578, 220915185448, 58949996, 4031986193, 115950, 29648, 280469],
                  0, -113),
            '2': ([28967139, 32227111122, 1311464430, 264567139422, 33356314, 24174473231, 1260767, 162, 1426963],
                  1, -113)
        }
    }),
    'node3': ({
        'ap2': {'oid': '12.109.103.48.50.49.50.48.51.51.56.49.53', 'status': '7'},
        'ap4': {'oid': '12.109.103.48.50.49.49.52.55.49.50.56.54', 'status': '7'},
        'ap5': {'oid': '12.109.103.48.50.49.50.48.51.52.48.49.53', 'status': '10'},
        'ap6': {'oid': '12.109.103.48.50.49.50.48.51.52.50.53.50', 'status': '7'}
    }, {
        '12.109.103.48.50.49.49.52.55.49.50.56.54': {
            '1': ([76919471, 88482655078, 1151204142, 228528823812, 356634591, 37901984374, 5124290, 992, 22365546],
                  0, -102),
            '2': ([5723407, 4034978261, 647754388, 174023660137, 87499187, 7415874135, 461152, 173, 1433566],
                  0, -115)
        },
        '12.109.103.48.50.49.50.48.51.51.56.49.53': {
            '1': ([46465371, 37306814965, 765295951, 193391950676, 70864936, 7263478701, 1737022, 975, 6706667],
                  0, -102),
            '2': ([34490476, 30642026963, 738087688, 182084036827, 87719129, 17243618794, 3398924, 196, 5457109],
                  0, -114)
        },
        '12.109.103.48.50.49.50.48.51.52.48.49.53': {
            '1': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0),
            '2': ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0)
        },
        '12.109.103.48.50.49.50.48.51.52.50.53.50': {
            '1': ([36144385, 38112823418, 1068977437, 220686191228, 582176451, 62550067378, 1396625, 463, 7581856],
                  0, -103),
            '2': ([9662814, 10893657649, 648933806, 174234350979, 83729153, 6702036409, 558807, 171, 1662070],
                  0, -118)
        }
    })
}
DISCOVERD_ITEMS = {
    'node1': ['ap1', 'ap2', 'ap3'],
    'node2': ['ap4', 'ap1', 'ap5', 'ap6', 'ap3'],
    'node3': ['ap4', 'ap2', 'ap5', 'ap6'],
}


@pytest.mark.parametrize("section,parsed_sections", [
    ([[['1', '0']]], (1, 0)),
])
def test_parse_juniper_trpz_aps(section, parsed_sections):  # type: ignore
    section = parse_juniper_trpz_aps(section)
    assert section == parsed_sections


@pytest.mark.parametrize("section,expected_results", [
    ((1, 0), [
        Metric('ap_devices_total', 1.0),
        Metric('total_sessions', 0.0),
        Result(state=state.OK, summary='Online access points: 1, Sessions: 0'),
        ]),
])
def test_check_juniper_trpz_aps(section, expected_results):  # type: ignore
    results = list(check_juniper_trpz_aps(section))
    for r in results:
        print(r)
    assert results == expected_results


@pytest.mark.parametrize("node_sections,expected_results", [
    ({
        "node1": (1, 2),
        "node2": (3, 4)
    }, [
        Result(state=state.OK, summary='Total: 4 access points, Sessions: 6'),
        Metric('ap_devices_total', 4.0),
        Metric('total_sessions', 6.0),
        Result(state=state.OK, summary='[node1] Online access points: 1, Sessions: 2'),
        Result(state=state.OK, summary='[node2] Online access points: 3, Sessions: 4'),
    ]),
])
def test_cluster_check_juniper_trpz_aps(node_sections, expected_results):  # type: ignore
    results = list(cluster_check_juniper_trpz_aps(node_sections))
    for r in results:
        print(r)
    assert results == expected_results


@pytest.mark.parametrize("node_sections,parsed_sections", [
    (NODE_SECTIONS, PARSED_DATA),
])
def test_parse_juniper_trpz_aps_sessions(node_sections, parsed_sections):  # type: ignore
    assert {
        node_name: parse_juniper_trpz_aps_sessions(string_list)
        for node_name, string_list in node_sections.items()
    } == parsed_sections


@pytest.mark.parametrize("node_sections,expected_items", [
    (PARSED_DATA, DISCOVERD_ITEMS),
])
def test_discovery_juniper_trpz_aps_sessions(node_sections, expected_items):  # type: ignore
    services = {
        node_name:
        [service.item for service in discovery_juniper_trpz_aps_sessions(section)]  # type: ignore
        for node_name, section in node_sections.items()
    }
    assert services, expected_items


@pytest.mark.parametrize("node_sections,expected_results", [
    ({
        "node1": PARSED_DATA["node1"]
    }, [
        Result(state=state.OK, summary='[node1/n/A] Status: operational'),
        Result(state=state.OK, summary='Radio 1: Input: 0.00 Bit/s, Output: 0.00 Bit/s, Errors: 0, Resets: 0, Retries: 0, Sessions: 0, Noise: 0 dBm'),
        Result(state=state.OK, summary='Radio 2: Input: 0.00 Bit/s, Output: 0.00 Bit/s, Errors: 0, Resets: 0, Retries: 0, Sessions: 0, Noise: 0 dBm'),
        Metric('if_out_unicast', 0.0),
        Metric('if_out_unicast_octets', 0.0),
        Metric('if_out_non_unicast', 0.0),
        Metric('if_out_non_unicast_octets', 0.0),
        Metric('if_in_pkts', 0.0),
        Metric('if_in_octets', 0.0),
        Metric('wlan_physical_errors', 0.0),
        Metric('wlan_resets', 0.0),
        Metric('wlan_retries', 0.0),
        Metric('total_sessions', 0.0),
        Metric('noise_floor', 0.0),
    ]),
])
def test__check_common_juniper_trpz_aps_sessions_single(node_sections, expected_results):  # type: ignore
    now = 1600000000
    vs: Dict[str, Any] = {}
    for _ in range(2):
        results = list(_check_common_juniper_trpz_aps_sessions(vs, now, "ap1", node_sections))
    assert results == expected_results


@pytest.mark.parametrize("node_sections,expected_results", [
    (PARSED_DATA, [
        Result(state=state.OK, summary='[node2/n/A] Status: redundant'),
        Result(state=state.OK, summary='Radio 1: Input: 0.00 Bit/s, Output: 0.00 Bit/s, Errors: 0, Resets: 0, Retries: 0, Sessions: 0, Noise: 0 dBm'),
        Result(state=state.OK, summary='Radio 2: Input: 0.00 Bit/s, Output: 0.00 Bit/s, Errors: 0, Resets: 0, Retries: 0, Sessions: 0, Noise: 0 dBm'),
        Metric('if_out_unicast', 0.0),
        Metric('if_out_unicast_octets', 0.0),
        Metric('if_out_non_unicast', 0.0),
        Metric('if_out_non_unicast_octets', 0.0),
        Metric('if_in_pkts', 0.0),
        Metric('if_in_octets', 0.0),
        Metric('wlan_physical_errors', 0.0),
        Metric('wlan_resets', 0.0),
        Metric('wlan_retries', 0.0),
        Metric('total_sessions', 0.0),
        Metric('noise_floor', 0.0),
    ]),
])
def test__check_common_juniper_trpz_aps_sessions_cluster(node_sections, expected_results):  # type: ignore
    now = 1600000000
    vs: Dict[str, Any] = {}
    for _ in range(2):
        results = list(_check_common_juniper_trpz_aps_sessions(vs, now, "ap1", node_sections))
    assert results == expected_results


_ = __name__ == "__main__" and pytest.main(["-svv", "-T=unit", __file__])
