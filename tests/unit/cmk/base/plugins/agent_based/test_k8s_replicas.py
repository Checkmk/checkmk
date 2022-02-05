#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence, Union

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

import cmk.base.plugins.agent_based.k8s_replicas as k8s_replicas
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.k8s_replicas import (
    check_k8s_replicas,
    parse_k8s_surge,
    parse_k8s_unavailability,
)
from cmk.base.plugins.agent_based.utils.k8s import parse_json

pytestmark = pytest.mark.checks

section_unavailable_ok = [
    [
        '{"strategy_type": "RollingUpdate", "replicas": 2, "paused": null, "max_unavailable": 1, "ready_replicas": 1, "max_surge": "25%"}'
    ]
]

section_surge_ok = [
    [
        '{"strategy_type": "RollingUpdate", "replicas": 2, "paused": null, "max_unavailable": 1, "ready_replicas": 3, "max_surge": 1}'
    ]
]

section_unavailable_crit = [
    [
        '{"strategy_type": "RollingUpdate", "replicas": 2, "paused": null, "max_unavailable": 1, "ready_replicas": 0, "max_surge": "25%"}'
    ]
]

section_surge_crit = [
    [
        '{"strategy_type": "RollingUpdate", "replicas": 2, "paused": false, "max_unavailable": 4, "ready_replicas": 4, "max_surge": "25%"}'
    ]
]

section_paused = [
    [
        '{"strategy_type": "RollingUpdate", "replicas": 2, "paused": true, "max_unavailable": 1, "ready_replicas": 4, "max_surge": "25%"}'
    ]
]

section_recreate = [
    [
        '{"strategy_type": "Recreate", "replicas": 10, "paused": null, "max_unavailable": null, "ready_replicas": 0, "max_surge": null}'
    ]
]


@pytest.mark.parametrize(
    "section,expected_check_result",
    [
        pytest.param(
            section_unavailable_ok,
            [
                Result(state=State.OK, summary="Ready: 1/2"),
                Metric("ready_replicas", 1, levels=(4.0, 4.0), boundaries=(0.0, 2.0)),
                Metric("total_replicas", 2),
                Result(
                    state=State.OK,
                    summary="Strategy: RollingUpdate (max unavailable: 1, max surge: 25%)",
                ),
            ],
            id="1/2 ready replicas with RollingUpdate strategy and max 1 unavailable replica is OK",
        ),
        pytest.param(
            section_surge_ok,
            [
                Result(state=State.OK, summary="Ready: 3/2"),
                Metric("ready_replicas", 3, levels=(4.0, 4.0), boundaries=(0.0, 2.0)),
                Metric("total_replicas", 2),
                Result(
                    state=State.OK,
                    summary="Strategy: RollingUpdate (max unavailable: 1, max surge: 1)",
                ),
            ],
            id="3/2 ready replicas with RollingUpdate strategy and 1 max surge is OK",
        ),
        pytest.param(
            section_unavailable_crit,
            [
                Result(state=State.CRIT, summary="Ready: 0/2 (warn/crit below 1/2/1/2)"),
                Metric("ready_replicas", 0, levels=(4.0, 4.0), boundaries=(0.0, 2.0)),
                Metric("total_replicas", 2),
                Result(
                    state=State.OK,
                    summary="Strategy: RollingUpdate (max unavailable: 1, max surge: 25%)",
                ),
            ],
            id="0/2 ready replicas with RollingUpdate strategy and 1 max unavailable is CRIT",
        ),
        pytest.param(
            section_surge_crit,
            [
                Result(state=State.CRIT, summary="Ready: 4/2 (warn/crit at 4/2/4/2)"),
                Metric("ready_replicas", 4, levels=(4.0, 4.0), boundaries=(0.0, 2.0)),
                Metric("total_replicas", 2),
                Result(
                    state=State.OK,
                    summary="Strategy: RollingUpdate (max unavailable: 4, max surge: 25%)",
                ),
            ],
            id="4/2 ready replicas with RollingUpdate strategy and 25% max surge is CRIT",
        ),
        pytest.param(
            section_paused,
            [
                Result(state=State.OK, summary="Ready: 4/2"),
                Metric("ready_replicas", 4, boundaries=(0.0, 2.0)),
                Result(state=State.OK, summary="Paused"),
                Metric("total_replicas", 2),
                Result(
                    state=State.OK,
                    summary="Strategy: RollingUpdate (max unavailable: 1, max surge: 25%)",
                ),
            ],
            id="4/2 ready replicas in paused state is OK",
        ),
        pytest.param(
            section_recreate,
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
    section: StringTable,
    expected_check_result: Sequence[Union[Result, Metric]],
) -> None:
    check = fix_register.check_plugins[CheckPluginName("k8s_replicas")]
    assert list(check.check_function(section=parse_json(section))) == expected_check_result


@pytest.mark.parametrize(
    "max_surge,total_replicas,expected_upper_level",
    [
        (1, 4, 6),
        ("25%", 10, 14),
    ],
)
def test_surge_levels(
    max_surge: Union[str, int],
    total_replicas: int,
    expected_upper_level: int,
) -> None:
    assert parse_k8s_surge(max_surge, total_replicas) == expected_upper_level


@pytest.mark.parametrize(
    "max_unavailable,total_replicas,expected_lower_level",
    [
        (2, 5, 3),
        ("25%", 10, 7),
    ],
)
def test_unavailability_levels(
    max_unavailable: Union[str, int],
    total_replicas: int,
    expected_lower_level: int,
) -> None:
    assert parse_k8s_unavailability(max_unavailable, total_replicas) == expected_lower_level


def test_first_unavailable_time(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get_value_store():
        return {"unavailable": 1}

    monkeypatch.setattr(k8s_replicas, "get_value_store", mock_get_value_store)
    monkeypatch.setattr("time.time", lambda: 701.0)

    assert list(
        check_k8s_replicas(
            section={
                "ready_replicas": None,
                "replicas": None,
                "paused": None,
                "strategy_type": None,
            }
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="The replicas data has been missing: 11 minutes 40 seconds (warn/crit at 10 minutes 0 seconds/10 minutes 0 seconds)",
        )
    ]
