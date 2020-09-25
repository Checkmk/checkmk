#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from cmk.base.api.agent_based.type_defs import Parameters
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Service,
    State as state,
    Result,
    Metric,
)
import cmk.base.plugins.agent_based.sap_hana_license as sap_hana_license

SECTION = {
    'Y04 10': {
        'enforced': sap_hana_license.SAP_HANA_MAYBE(bool=False, value=u'FALSE'),
        'locked': sap_hana_license.SAP_HANA_MAYBE(bool=False, value=u'FALSE'),
        'expiration_date': u'2020-08-02 23:59:59.999999000',
        'permanent': sap_hana_license.SAP_HANA_MAYBE(bool=False, value=u'FALSE'),
        'limit': 2147483647,
        'valid': sap_hana_license.SAP_HANA_MAYBE(bool=True, value=u'TRUE'),
        'size': 33
    },
    'H62 10': {
        'enforced': sap_hana_license.SAP_HANA_MAYBE(bool=False, value=u'FALSE'),
        'locked': sap_hana_license.SAP_HANA_MAYBE(bool=False, value=u'FALSE'),
        'expiration_date': u'?',
        'permanent': sap_hana_license.SAP_HANA_MAYBE(bool=True, value=u'TRUE'),
        'limit': 12300,
        'valid': sap_hana_license.SAP_HANA_MAYBE(bool=True, value=u'TRUE'),
        'size': 19
    },
    'X04 55': {
        'enforced': sap_hana_license.SAP_HANA_MAYBE(bool=True, value=u'TRUE'),
        'locked': sap_hana_license.SAP_HANA_MAYBE(bool=False, value=u'FALSE'),
        'expiration_date': u'2020-08-02 23:59:59.999999000',
        'permanent': sap_hana_license.SAP_HANA_MAYBE(bool=False, value=u'FALSE'),
        'limit': 10,
        'valid': sap_hana_license.SAP_HANA_MAYBE(bool=True, value=u'TRUE'),
        'size': 5
    },
    'X00 00': {
        'enforced': sap_hana_license.SAP_HANA_MAYBE(bool=True, value=u'TRUE'),
        'locked': sap_hana_license.SAP_HANA_MAYBE(bool=False, value=u'FALSE'),
        'expiration_date': u'2020-08-02 23:59:59.999999000',
        'permanent': sap_hana_license.SAP_HANA_MAYBE(bool=False, value=u'FALSE'),
        'limit': 0,
        'valid': sap_hana_license.SAP_HANA_MAYBE(bool=True, value=u'TRUE'),
        'size': 5
    }
}


@pytest.mark.parametrize("string_table_row, expected_parsed_data", [
    (
        [
            ['[[H62 10]]'],
            ['FALSE', 'TRUE', 'FALSE', '19', '12300', 'TRUE', '?'],
        ],
        {
            "H62 10": SECTION["H62 10"]
        },
    ),
    (
        [['[[Y04 10]]'],
         ['FALSE', 'FALSE', 'FALSE', '33', '2147483647', 'TRUE', '2020-08-02 23:59:59.999999000']],
        {
            "Y04 10": SECTION["Y04 10"]
        },
    ),
    (
        [['[[X04 55]]'],
         ['TRUE', 'FALSE', 'FALSE', '5', '10', 'TRUE', '2020-08-02 23:59:59.999999000']],
        {
            "X04 55": SECTION["X04 55"]
        },
    ),
])
def test_sap_hana_license_parse(string_table_row, expected_parsed_data):
    assert sap_hana_license.parse_sap_hana_license(string_table_row) == expected_parsed_data


def test_sap_hana_license_discovery():
    assert list(sap_hana_license.discovery_sap_hana_license(SECTION)) == [
        Service(item='Y04 10', parameters={}, labels=[]),
        Service(item='H62 10', parameters={}, labels=[]),
        Service(item='X04 55', parameters={}, labels=[]),
        Service(item='X00 00', parameters={}, labels=[]),
    ]


@pytest.mark.parametrize(
    "cur_item, result",
    [("Y04 10", [
        Result(state=state.OK, summary='Status: unlimited', details='Status: unlimited'),
        Result(state=state.WARN, summary='License: not FALSE', details='License: not FALSE'),
        Result(state=state.WARN,
               summary='Expiration date: 2020-08-02 23:59:59.999999000',
               details='Expiration date: 2020-08-02 23:59:59.999999000'),
    ]),
     ("H62 10", [
         Result(state=state.OK, summary='Status: unlimited', details='Status: unlimited'),
         Result(state=state.OK, summary='License: TRUE', details='License: TRUE'),
     ]),
     ("X04 55", [
         Result(state=state.OK, summary='Size: 5 B', details='Size: 5 B'),
         Metric('license_size', 5.0, levels=(None, None), boundaries=(None, None)),
         Result(state=state.OK, summary='Usage: 50.0%', details='Usage: 50.0%'),
         Metric('license_usage_perc', 50.0, levels=(None, None), boundaries=(None, None)),
         Result(state=state.WARN, summary='License: not FALSE', details='License: not FALSE'),
         Result(state=state.WARN,
                summary='Expiration date: 2020-08-02 23:59:59.999999000',
                details='Expiration date: 2020-08-02 23:59:59.999999000'),
     ]),
     (
         "X00 00",
         [
             Result(state=state.OK, summary='Size: 5 B', details='Size: 5 B'),
             Metric('license_size', 5.0, levels=(None, None), boundaries=(None, None)),
             Result(state=state.WARN,
                    summary='Usage: cannot calculate',
                    details='Usage: cannot calculate'),
             Result(state=state.WARN, summary='License: not FALSE', details='License: not FALSE'),
             Result(state=state.WARN,
                    summary='Expiration date: 2020-08-02 23:59:59.999999000',
                    details='Expiration date: 2020-08-02 23:59:59.999999000'),
         ],
     )])
def test_sap_hana_license_check(cur_item, result):
    yielded_results = list(
        sap_hana_license.check_sap_hana_license(cur_item, Parameters({}), SECTION))
    assert yielded_results == result
