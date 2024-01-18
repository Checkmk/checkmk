#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from typing import Any

import pytest

from tests.unit.conftest import FixRegister

from cmk.checkengine.checking import CheckPluginName

from cmk.base.legacy_checks import mem
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult

from cmk.agent_based.prediction_backend import (
    InjectedParameters,
    PredictionInfo,
    PredictionParameters,
)

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


PREDICTIVE_PARAMS = PredictionParameters(
    period="minute",
    horizon=90,
    levels=("relative", (10.0, 20.0)),
)

PREDICTED_VALUE_MEM = 104857600000
META_MEM = PredictionInfo.make("mem_used", "upper", PREDICTIVE_PARAMS, time.time())
INJECTED_MEM = InjectedParameters(
    meta_file_path_template="",
    predictions={
        hash(META_MEM): (
            PREDICTED_VALUE_MEM,
            (int(PREDICTED_VALUE_MEM * 0.9), int(PREDICTED_VALUE_MEM * 1.1)),
        )
    },
)


PREDICTED_VALUE_PGF = 100000000000
META_PGF = PredictionInfo.make("pagefile_used", "upper", PREDICTIVE_PARAMS, time.time())
INJECTED_PGF = InjectedParameters(
    meta_file_path_template="",
    predictions={
        hash(META_PGF): (
            PREDICTED_VALUE_PGF,
            (int(PREDICTED_VALUE_PGF * 0.9), int(PREDICTED_VALUE_PGF * 1.1)),
        )
    },
)


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            mem.Params(
                memory=("perc_used", (80.0, 90.0)),
                pagefile=("perc_used", (70.0, 90.0)),
            ),
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
            mem.Params(
                memory=("abs_free", (2097152000, 1048576000)),
                pagefile=("abs_free", (52428800000, 4194304000)),
                average=10,
            ),
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
            mem.Params(
                memory=(
                    "predictive",
                    {
                        "horizon": PREDICTIVE_PARAMS.horizon,
                        "period": PREDICTIVE_PARAMS.period,
                        "levels_upper": PREDICTIVE_PARAMS.levels,
                        "__injected__": INJECTED_MEM.model_dump(),
                    },
                ),
                pagefile=(
                    "predictive",
                    {
                        "horizon": PREDICTIVE_PARAMS.horizon,
                        "period": PREDICTIVE_PARAMS.period,
                        "levels_upper": PREDICTIVE_PARAMS.levels,
                        "__injected__": INJECTED_PGF.model_dump(),
                    },
                ),
            ),
            [
                Metric("mem_total", 131071.421875),
                Result(
                    state=State.WARN,
                    summary="RAM: 81.51% - 104 GiB of 128 GiB, RAM: 104 GiB (predicted reference: 97.7 GiB) (warn/crit at 87.9 GiB/107 GiB)",
                ),
                Metric("mem_used", 112020467712.0, boundaries=(0.0, 137438347264.0)),
                Metric("mem_used_percent", 81.50597700132717, boundaries=(0.0, None)),
                Metric("predict_mem_used", PREDICTED_VALUE_MEM),
                Metric("pagefile_total", 150527.421875),
                Result(
                    state=State.CRIT,
                    summary="Commit charge: 75.43% - 111 GiB of 147 GiB, Commit charge: 111 GiB (predicted reference: 93.1 GiB) (warn/crit at 83.8 GiB/102 GiB)",
                ),
                Metric("pagefile_used", 119057674240.0, boundaries=(0.0, 157839441920.0)),
                Metric("predict_pagefile_used", PREDICTED_VALUE_PGF),
            ],
            id="predictive levels",
        ),
        pytest.param(
            mem.Params(
                memory=(
                    "predictive",
                    {
                        "horizon": PREDICTIVE_PARAMS.horizon,
                        "period": PREDICTIVE_PARAMS.period,
                        "levels_upper": PREDICTIVE_PARAMS.levels,
                        "__injected__": INJECTED_MEM.model_dump(),
                    },
                ),
                pagefile=(
                    "predictive",
                    {
                        "horizon": PREDICTIVE_PARAMS.horizon,
                        "period": PREDICTIVE_PARAMS.period,
                        "levels_upper": PREDICTIVE_PARAMS.levels,
                        "__injected__": INJECTED_PGF.model_dump(),
                    },
                ),
                average=60,
            ),
            [
                Metric("mem_total", 131071.421875),
                Result(
                    state=State.WARN,
                    summary="RAM: 81.51% - 104 GiB of 128 GiB, 60 min average: 81.51% (104 GiB), RAM: 104 GiB (predicted reference: 97.7 GiB) (warn/crit at 87.9 GiB/107 GiB)",
                ),
                Metric("mem_used", 112020467712.0, boundaries=(0.0, 137438347264.0)),
                Metric("mem_used_percent", 81.50597700132717, boundaries=(0.0, None)),
                Metric("mem_used_avg", 112020467712.0, boundaries=(0.0, 137438347264.0)),
                Metric("predict_mem_used", PREDICTED_VALUE_MEM),
                Metric("pagefile_total", 150527.421875),
                Result(
                    state=State.CRIT,
                    summary="Commit charge: 75.43% - 111 GiB of 147 GiB, 60 min average: 75.43% (111 GiB), Commit charge: 111 GiB (predicted reference: 93.1 GiB) (warn/crit at 83.8 GiB/102 GiB)",
                ),
                Metric("pagefile_used", 119057674240.0, boundaries=(0.0, 157839441920.0)),
                Metric("pagefile_used_avg", 119057674240.0, boundaries=(0.0, 157839441920.0)),
                Metric("predict_pagefile_used", PREDICTED_VALUE_PGF),
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
