#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from pathlib import Path
from unittest.mock import Mock

from cmk.agent_based.prediction_backend import (
    InjectedParameters,
    PredictionInfo,
    PredictionParameters,
)
from cmk.agent_based.v1 import Metric, Result, State
from cmk.plugins.lib.cpu import Load, ProcessorType, Section, Threads
from cmk.plugins.lib.cpu_load import check_cpu_load


def test_cpu_loads_fixed_levels() -> None:
    assert list(
        check_cpu_load(
            {
                "levels1": None,
                "levels5": None,
                "levels15": (2.0, 4.0),
            },
            Section(
                load=Load(0.5, 1.0, 1.5),
                num_cpus=4,
                threads=Threads(count=123),
                type=ProcessorType.physical,
            ),
        )
    ) == [
        Result(state=State.OK, summary="15 min load: 1.50"),
        Metric("load15", 1.5, levels=(8.0, 16.0)),  # levels multiplied by num_cpus
        Result(state=State.OK, summary="15 min load per core: 0.38 (4 physical cores)"),
        Result(state=State.OK, notice="1 min load: 0.50"),
        Metric("load1", 0.5, boundaries=(0, 4)),  # levels multiplied by num_cpus
        Result(state=State.OK, notice="1 min load per core: 0.12 (4 physical cores)"),
        Result(state=State.OK, notice="5 min load: 1.00"),
        Metric("load5", 1.0),  # levels multiplied by num_cpus
        Result(state=State.OK, notice="5 min load per core: 0.25 (4 physical cores)"),
    ]


def test_cpu_loads_predictive(mocker: Mock, tmp_path: Path) -> None:
    prep_u = PredictionParameters(
        period="minute", horizon=1, levels=("absolute", (2.0, 4.0)), bound=None
    )
    meta_u = PredictionInfo.make(metric="load15", direction="upper", params=prep_u, now=time.time())

    # make sure cpu_load check can handle predictive values
    assert list(
        check_cpu_load(
            {
                "levels1": None,
                "levels5": None,
                "levels15": {
                    "period": prep_u.period,
                    "horizon": prep_u.horizon,
                    "levels_upper": prep_u.levels,
                    "__injected__": InjectedParameters(
                        meta_file_path_template=str(tmp_path),
                        predictions={hash(meta_u): (None, (2.2, 4.2))},
                    ).model_dump(),
                },
            },
            Section(
                load=Load(0.5, 1.0, 1.5),
                num_cpus=4,
                threads=Threads(count=123),
            ),
        )
    ) == [
        Result(state=State.OK, summary="15 min load: 1.50 (no reference for prediction yet)"),
        Metric("load15", 1.5, levels=(2.2, 4.2)),  # those are the predicted values
        Result(state=State.OK, summary="15 min load per core: 0.38 (4 cores)"),
        Result(state=State.OK, notice="1 min load: 0.50"),
        Metric("load1", 0.5, boundaries=(0, 4)),
        Result(state=State.OK, notice="1 min load per core: 0.12 (4 cores)"),
        Result(state=State.OK, notice="5 min load: 1.00"),
        Metric("load5", 1.0),
        Result(state=State.OK, notice="5 min load per core: 0.25 (4 cores)"),
    ]
