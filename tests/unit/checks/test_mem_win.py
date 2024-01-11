#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

import pytest

from tests.unit.conftest import FixRegister

from cmk.checkengine.checking import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult

_SECTION = {
    "MemTotal": 137438347264,
    "MemFree": 25417879552,
    "SwapTotal": 20401094656,
    "SwapFree": 13363888128,
    "PageTotal": 157839441920,
    "PageFree": 38781767680,
    "VirtualTotal": 140737488224256,
    "VirtualFree": 140737374928896,
}


_PREDICTED_VALUE = 104857600000


def _get_prediction(
    metric: str, levels_factor: float
) -> tuple[float, tuple[float, float, None, None]]:
    return _PREDICTED_VALUE, (int(_PREDICTED_VALUE * 0.9), int(_PREDICTED_VALUE * 1.1), None, None)


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {
                "memory": (80.0, 90.0),
                "pagefile": (70.0, 90.0),
            },
            [
                Metric("mem_total", 131071.421875),
                Result(
                    state=State.WARN,
                    summary="RAM: 81.51% - 104 GiB of 128 GiB (warn/crit at 80.00%/90.00% used)",
                ),
                Metric(
                    "mem_used",
                    112020467712.0,
                    levels=(109950677811.20001, 123694512537.6),
                    boundaries=(0.0, 137438347264.0),
                ),
                Metric(
                    "mem_used_percent",
                    81.50597700132717,
                    levels=(80.00000000000001, 90.00000000000001),
                    boundaries=(0.0, None),
                ),
                Metric("pagefile_total", 150527.421875),
                Result(
                    state=State.WARN,
                    summary="Commit charge: 75.43% - 111 GiB of 147 GiB (warn/crit at 70.00%/90.00% used)",
                ),
                Metric(
                    "pagefile_used",
                    119057674240.0,
                    levels=(110487609344.0, 142055497728.0),
                    boundaries=(0.0, 157839441920.0),
                ),
            ],
            id="normal levels",
        ),
        pytest.param(
            {
                "memory": (2000, 1000),
                "pagefile": (50000, 4000),
                "average": 10,
            },
            [
                Metric("mem_total", 131071.421875),
                Result(
                    state=State.OK,
                    summary="RAM: 81.51% - 104 GiB of 128 GiB, 10 min average: 81.51% (104 GiB)",
                ),
                Metric("mem_used", 112020467712.0, boundaries=(0.0, 137438347264.0)),
                Metric("mem_used_percent", 81.50597700132717, boundaries=(0.0, None)),
                Metric(
                    "mem_used_avg",
                    112020467712.0,
                    levels=(135341195264.0, 136389771264.0),
                    boundaries=(0.0, 137438347264.0),
                ),
                Metric("pagefile_total", 150527.421875),
                Result(
                    state=State.WARN,
                    summary="Commit charge: 75.43% - 111 GiB of 147 GiB, 10 min average: 75.43% (111 GiB)",
                ),
                Metric("pagefile_used", 119057674240.0, boundaries=(0.0, 157839441920.0)),
                Metric(
                    "pagefile_used_avg",
                    119057674240.0,
                    levels=(105410641920.0, 153645137920.0),
                    boundaries=(0.0, 157839441920.0),
                ),
            ],
            id="normal levels + averaging",
        ),
        pytest.param(
            {
                "memory": {
                    "period": "minute",
                    "horizon": 90,
                    "levels_upper": ("relative", (10.0, 20.0)),
                    "__get_predictive_levels__": _get_prediction,
                },
                "pagefile": {
                    "period": "minute",
                    "horizon": 90,
                    "levels_upper": ("relative", (10.0, 20.0)),
                    "__get_predictive_levels__": _get_prediction,
                },
            },
            [
                Metric("mem_total", 131071.421875),
                Result(
                    state=State.WARN,
                    summary="RAM: 81.51% - 104 GiB of 128 GiB, RAM: 104.33 GiB (predicted reference: 97.66) (warn/crit at 87.89 GiB/107.42 GiB)",
                ),
                Metric("mem_used", 112020467712.0, boundaries=(0.0, 137438347264.0)),
                Metric("mem_used_percent", 81.50597700132717, boundaries=(0.0, None)),
                Metric("predict_mem_used", _PREDICTED_VALUE),
                Metric("pagefile_total", 150527.421875),
                Result(
                    state=State.CRIT,
                    summary="Commit charge: 75.43% - 111 GiB of 147 GiB, Commit charge: 110.88 GiB (predicted reference: 97.66) (warn/crit at 87.89 GiB/107.42 GiB)",
                ),
                Metric("pagefile_used", 119057674240.0, boundaries=(0.0, 157839441920.0)),
                Metric("predict_pagefile_used", _PREDICTED_VALUE),
            ],
            id="predictive levels",
        ),
        pytest.param(
            {
                "memory": {
                    "period": "minute",
                    "horizon": 90,
                    "levels_upper": ("relative", (10.0, 20.0)),
                    "__get_predictive_levels__": _get_prediction,
                },
                "pagefile": {
                    "period": "minute",
                    "horizon": 90,
                    "levels_upper": ("relative", (10.0, 20.0)),
                    "__get_predictive_levels__": _get_prediction,
                },
                "average": 60,
            },
            [
                Metric("mem_total", 131071.421875),
                Result(
                    state=State.WARN,
                    summary="RAM: 81.51% - 104 GiB of 128 GiB, 60 min average: 81.51% (104 GiB), RAM: 104.33 GiB (predicted reference: 97.66) (warn/crit at 87.89 GiB/107.42 GiB)",
                ),
                Metric("mem_used", 112020467712.0, boundaries=(0.0, 137438347264.0)),
                Metric("mem_used_percent", 81.50597700132717, boundaries=(0.0, None)),
                Metric("mem_used_avg", 112020467712.0, boundaries=(0.0, 137438347264.0)),
                Metric("predict_mem_used", _PREDICTED_VALUE),
                Metric("pagefile_total", 150527.421875),
                Result(
                    state=State.CRIT,
                    summary="Commit charge: 75.43% - 111 GiB of 147 GiB, 60 min average: 75.43% (111 GiB), Commit charge: 110.88 GiB (predicted reference: 97.66) (warn/crit at 87.89 GiB/107.42 GiB)",
                ),
                Metric("pagefile_used", 119057674240.0, boundaries=(0.0, 157839441920.0)),
                Metric("pagefile_used_avg", 119057674240.0, boundaries=(0.0, 157839441920.0)),
                Metric("predict_pagefile_used", _PREDICTED_VALUE),
            ],
            id="predictive levels + averaging",
        ),
    ],
)
def test_mem_win(
    fix_register: FixRegister,
    params: Mapping[str, Any],
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            fix_register.check_plugins[CheckPluginName("mem_win")].check_function(
                item=None,
                params=params,
                section=_SECTION,
            )
        )
        == expected_result
    )
