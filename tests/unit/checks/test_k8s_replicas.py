#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]
from checktestlib import CheckResult, assertCheckResultsEqual

from cmk.base.plugins.agent_based.utils.k8s import parse_json

pytestmark = pytest.mark.checks

info_unavailable_ok = [[
    u'{"strategy_type": "RollingUpdate", "replicas": 2, "paused": null, "max_unavailable": 1, "ready_replicas": 1, "max_surge": "25%"}'
]]

info_surge_ok = [[
    u'{"strategy_type": "RollingUpdate", "replicas": 2, "paused": null, "max_unavailable": 1, "ready_replicas": 3, "max_surge": 1}'
]]

info_unavailable_crit = [[
    u'{"strategy_type": "RollingUpdate", "replicas": 2, "paused": null, "max_unavailable": 1, "ready_replicas": 0, "max_surge": "25%"}'
]]

info_surge_crit = [[
    u'{"strategy_type": "RollingUpdate", "replicas": 2, "paused": false, "max_unavailable": 1, "ready_replicas": 4, "max_surge": "25%"}'
]]

info_paused = [[
    u'{"strategy_type": "RollingUpdate", "replicas": 2, "paused": true, "max_unavailable": 1, "ready_replicas": 4, "max_surge": "25%"}'
]]

info_recreate = [[
    u'{"strategy_type": "Recreate", "replicas": 10, "paused": null, "max_unavailable": null, "ready_replicas": 0, "max_surge": null}'
]]


@pytest.mark.parametrize("info,expected", [
    (
        info_unavailable_ok,
        [
            (0, 'Ready: 1/2', [
                ('ready_replicas', 1, None, 4.0, None, None),
                ('total_replicas', 2, None, None, None, None),
            ]),
            (0, u'Strategy: RollingUpdate (max unavailable: 1, max surge: 25%)', []),
        ],
    ),
    (
        info_surge_ok,
        [
            (0, 'Ready: 3/2', [
                ('ready_replicas', 3, None, 4.0, None, None),
                ('total_replicas', 2, None, None, None, None),
            ]),
            (0, u'Strategy: RollingUpdate (max unavailable: 1, max surge: 1)', []),
        ],
    ),
    (
        info_unavailable_crit,
        [
            (2, 'Ready: 0/2 (crit below 1)', [
                ('ready_replicas', 0, None, 4.0, None, None),
                ('total_replicas', 2, None, None, None, None),
            ]),
            (0, u'Strategy: RollingUpdate (max unavailable: 1, max surge: 25%)', []),
        ],
    ),
    (
        info_surge_crit,
        [
            (2, 'Ready: 4/2 (crit at 4)', [
                ('ready_replicas', 4, None, 4.0, None, None),
                ('total_replicas', 2, None, None, None, None),
            ]),
            (0, u'Strategy: RollingUpdate (max unavailable: 1, max surge: 25%)', []),
        ],
    ),
    (
        info_paused,
        [
            (0, 'Ready: 4/2 (paused)', [
                ('ready_replicas', 4, None, None, None, None),
                ('total_replicas', 2, None, None, None, None),
            ]),
            (0, u'Strategy: RollingUpdate (max unavailable: 1, max surge: 25%)', []),
        ],
    ),
    (
        info_recreate,
        [
            (0, 'Ready: 0/10', [
                ('ready_replicas', 0, None, None, None, None),
                ('total_replicas', 10, None, None, None, None),
            ]),
            (0, u'Strategy: Recreate', []),
        ],
    ),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_k8s_replicas(info, expected):
    check = Check("k8s_replicas")
    parsed = parse_json(info)
    actual = check.run_check(None, {}, parsed)

    assertCheckResultsEqual(
        CheckResult(actual),
        CheckResult(expected),
    )


@pytest.mark.parametrize('max_surge,total,expected', [
    (1, 4, 6),
    ('25%', 10, 14),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_surge_levels(max_surge, total, expected):
    check = Check('k8s_replicas')
    crit = check.context['parse_k8s_surge'](max_surge, total)
    assert crit == expected


@pytest.mark.parametrize('max_unavailable,total,expected', [
    (2, 5, 3),
    ('25%', 10, 7),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_unavailability_levels(max_unavailable, total, expected):
    check = Check('k8s_replicas')
    crit_lower = check.context['parse_k8s_unavailability'](max_unavailable, total)
    assert crit_lower == expected
