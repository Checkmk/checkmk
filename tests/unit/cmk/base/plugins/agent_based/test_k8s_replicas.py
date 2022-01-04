#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence, Union

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.utils.k8s import parse_json

pytestmark = pytest.mark.checks

info_unavailable_ok = [
    [
        '{"strategy_type": "RollingUpdate", "replicas": 2, "paused": null, "max_unavailable": 1, "ready_replicas": 1, "max_surge": "25%"}'
    ]
]

info_surge_ok = [
    [
        '{"strategy_type": "RollingUpdate", "replicas": 2, "paused": null, "max_unavailable": 1, "ready_replicas": 3, "max_surge": 1}'
    ]
]

info_unavailable_crit = [
    [
        '{"strategy_type": "RollingUpdate", "replicas": 2, "paused": null, "max_unavailable": 1, "ready_replicas": 0, "max_surge": "25%"}'
    ]
]

info_surge_crit = [
    [
        '{"strategy_type": "RollingUpdate", "replicas": 2, "paused": false, "max_unavailable": 4, "ready_replicas": 4, "max_surge": "25%"}'
    ]
]

info_paused = [
    [
        '{"strategy_type": "RollingUpdate", "replicas": 2, "paused": true, "max_unavailable": 1, "ready_replicas": 4, "max_surge": "25%"}'
    ]
]

info_recreate = [
    [
        '{"strategy_type": "Recreate", "replicas": 10, "paused": null, "max_unavailable": null, "ready_replicas": 0, "max_surge": null}'
    ]
]


@pytest.mark.parametrize(
    "info,expected",
    [
        pytest.param(
            info_unavailable_ok,
            [
                Result(state=State.OK, summary="Ready: 1/2"),
                Metric("ready_replicas", 1, levels=(None, 4.0), boundaries=(0.0, 2.0)),
                Metric("total_replicas", 2),
                Result(
                    state=State.OK,
                    summary="Strategy: RollingUpdate (max unavailable: 1, max surge: 25%)",
                ),
            ],
            id="1/2 ready replicas with RollingUpdate strategy and max 1 unavailable replica is OK",
        ),
        pytest.param(
            info_surge_ok,
            [
                Result(state=State.OK, summary="Ready: 3/2"),
                Metric("ready_replicas", 3, levels=(None, 4.0), boundaries=(0.0, 2.0)),
                Metric("total_replicas", 2),
                Result(
                    state=State.OK,
                    summary="Strategy: RollingUpdate (max unavailable: 1, max surge: 1)",
                ),
            ],
            id="3/2 ready replicas with RollingUpdate strategy and 1 max surge is OK",
        ),
        pytest.param(
            info_unavailable_crit,
            [
                Result(state=State.CRIT, summary="Ready: 0/2 (crit below 1)"),
                Metric("ready_replicas", 0, levels=(None, 4.0), boundaries=(0.0, 2.0)),
                Metric("total_replicas", 2),
                Result(
                    state=State.OK,
                    summary="Strategy: RollingUpdate (max unavailable: 1, max surge: 25%)",
                ),
            ],
            id="0/2 ready replicas with RollingUpdate strategy and 1 max unavailable is CRIT",
        ),
        pytest.param(
            info_surge_crit,
            [
                Result(state=State.CRIT, summary="Ready: 4/2 (crit at 4)"),
                Metric("ready_replicas", 4, levels=(None, 4.0), boundaries=(0.0, 2.0)),
                Metric("total_replicas", 2),
                Result(
                    state=State.OK,
                    summary="Strategy: RollingUpdate (max unavailable: 4, max surge: 25%)",
                ),
            ],
            id="4/2 ready replicas with RollingUpdate strategy and 25% max surge is CRIT",
        ),
        pytest.param(
            info_paused,
            [
                Result(state=State.OK, summary="Ready: 4/2 (paused)"),
                Metric("ready_replicas", 4, boundaries=(0.0, 2.0)),
                Metric("total_replicas", 2),
                Result(
                    state=State.OK,
                    summary="Strategy: RollingUpdate (max unavailable: 1, max surge: 25%)",
                ),
            ],
            id="4/2 ready replicas in paused state is OK",
        ),
        pytest.param(
            info_recreate,
            [
                Result(state=State.OK, summary="Ready: 0/10"),
                Metric("ready_replicas", 0, boundaries=(0.0, 10.0)),
                Metric("total_replicas", 10),
                Result(state=State.OK, summary="Strategy: Recreate"),
            ],
            id="0/10 ready replicas and Recreate strategy is OK",
        ),
    ],
)
def test_k8s_replicas(
    fix_register: FixRegister,
    info: StringTable,
    expected: Sequence[Union[Result, Metric]],
) -> None:
    check = fix_register.check_plugins[CheckPluginName("k8s_replicas")]
    assert list(check.check_function(item=None, params={}, section=parse_json(info))) == expected
