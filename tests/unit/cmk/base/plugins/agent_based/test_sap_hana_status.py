#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from cmk.base.plugins.agent_based.agent_based_api.v1 import Service, State as state, Result, Metric
import cmk.base.plugins.agent_based.sap_hana_status as sap_hana_status

ITEM = "H90 33"
SECTION = {
    'Status %s' % ITEM: {
        'instance': ITEM,
        'message': 'Yes',
        'state_name': 'OK'
    },
    'Version %s' % ITEM: {
        'instance': ITEM,
        'version': '1.00.122.22.1543461992 (fa/hana1sp12)'
    }
}
SECTION_WARNING = {
    'Status %s' % ITEM: {
        'instance': ITEM,
        'message': 'Yes',
        'state_name': 'WARNING'
    },
    'Version %s' % ITEM: {
        'instance': ITEM,
        'version': '1.00.122.22.1543461992 (fa/hana1sp12)'
    }
}


@pytest.mark.parametrize("string_table_row, expected_parsed_data", [([
    ['[[H62 10]]'],
    ['Version', '', '1.00.122.22.1543461992 (fa/hana1sp12)'],
    ['All Started', 'OK', 'Yes'],
    ['[[H90 33]]'],
    ['Version', '', '1.00.122.22.1543461992 (fa/hana1sp12)'],
    ['All Started', 'OK', 'Yes'],
], {
    'Status H62 10': {
        'instance': 'H62 10',
        'message': 'Yes',
        'state_name': 'OK'
    },
    'Version H62 10': {
        'instance': 'H62 10',
        'version': '1.00.122.22.1543461992 (fa/hana1sp12)'
    },
    'Status H90 33': {
        'instance': 'H90 33',
        'message': 'Yes',
        'state_name': 'OK'
    },
    'Version H90 33': {
        'instance': 'H90 33',
        'version': '1.00.122.22.1543461992 (fa/hana1sp12)'
    }
})])
def test_sap_hana_status_parse(string_table_row, expected_parsed_data):
    assert sap_hana_status.parse_sap_hana_status(string_table_row) == expected_parsed_data


def test_sap_hana_status_discovery():
    assert list(sap_hana_status.discovery_sap_hana_status(SECTION)) == [
        Service(item="Status %s" % ITEM),
        Service(item="Version %s" % ITEM),
    ]


@pytest.mark.parametrize(
    "section, check_type, results",
    [(SECTION, "Status", Result(state=state.OK, summary='Status: OK', details='Status: OK')),
     (
         SECTION,
         "Version",
         Result(state=state.OK,
                summary='Version: 1.00.122.22.1543461992 (fa/hana1sp12)',
                details='Version: 1.00.122.22.1543461992 (fa/hana1sp12)'),
     ),
     (SECTION_WARNING, "Status",
      Result(state=state.WARN, summary='Status: WARNING', details='Status: WARNING'))])
def test_sap_hana_status_check(check_type, results, section):

    yielded_results = list(
        sap_hana_status.check_sap_hana_status("%s %s" % (check_type, ITEM), section))
    assert yielded_results == [results]


def test_sap_hana_status_cluster_check():
    section = {"node 1": SECTION, "node 2": SECTION_WARNING}
    yielded_results = list(
        sap_hana_status.cluster_check_sap_hana_status("Status %s" % ITEM, section))
    assert yielded_results == [
        Result(state=state.OK, summary='Nodes: node 1, node 2', details='Nodes: node 1, node 2'),
        Result(state=state.OK, summary='Status: OK', details='Status: OK')
    ]
