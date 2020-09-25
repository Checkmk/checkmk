#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Metric,
    Result,
    State as state,
    type_defs,
)
from cmk.base.plugins.agent_based import netscaler_sslcertificates

PARAMS = type_defs.Parameters({
    "age_levels": (30, 10),
})

SECTION = {
    'cert1': 1123,
    'cert2': 7,
}


def test_check_netscaler_sslcertificates_ok():
    assert list(netscaler_sslcertificates.check_netscaler_sslcertificates(
        "cert1",
        PARAMS,
        SECTION,
    )) == [
        Result(state=state.OK, summary='certificate valid for: 1123 days'),
        Metric('daysleft', 1123.0, levels=(None, None), boundaries=(None, None)),
    ]


def test_check_netscaler_sslcertificates_crit():
    assert list(netscaler_sslcertificates.check_netscaler_sslcertificates(
        "cert2",
        PARAMS,
        SECTION,
    )) == [
        Result(state=state.CRIT,
               summary='certificate valid for: 7 days (warn/crit below 30 days/10 days)'),
        Metric('daysleft', 7.0, levels=(None, None), boundaries=(None, None)),
    ]


def test_cluster_check_netscaler_sslcertificates_ok():
    assert list(
        netscaler_sslcertificates.cluster_check_netscaler_sslcertificates(
            "cert1",
            PARAMS,
            {
                'node1': SECTION,
                'node2': {
                    'cert3': 123,
                },
            },
        )) == [
            Result(state=state.OK, summary='[node1]: certificate valid for: 1123 days'),
            Metric('daysleft', 1123.0, levels=(None, None), boundaries=(None, None)),
        ]


def test_cluster_check_netscaler_sslcertificates_crit():
    assert list(
        netscaler_sslcertificates.cluster_check_netscaler_sslcertificates(
            "cert2",
            PARAMS,
            {
                'node1': SECTION,
                'node2': SECTION,
            },
        )) == [
            Result(
                state=state.CRIT,
                summary='[node1]: certificate valid for: 7 days (warn/crit below 30 days/10 days)'),
            Metric('daysleft', 7.0, levels=(None, None), boundaries=(None, None)),
            Result(
                state=state.CRIT,
                summary='[node2]: certificate valid for: 7 days (warn/crit below 30 days/10 days)'),
            Metric('daysleft', 7.0, levels=(None, None), boundaries=(None, None)),
        ]
