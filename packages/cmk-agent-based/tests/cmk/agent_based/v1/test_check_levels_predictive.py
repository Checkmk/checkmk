#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from pathlib import Path

from cmk.agent_based.prediction_backend import PredictionInfo, PredictionParameters
from cmk.agent_based.v1 import check_levels_predictive, Result

_PredictiveLevels = tuple[
    float | None, tuple[float | None, float | None, float | None, float | None]
]


def _get_test_levels_v1(metric: str, template: str) -> dict[str, object]:
    params = PredictionParameters(
        horizon=90,
        period="wday",
        levels=("absolute", (23.0, 42.0)),
    )
    meta = PredictionInfo.make(metric, "upper", params, time.time())
    return {
        "period": params.period,
        "horizon": params.horizon,
        "levels_upper": params.levels,
        "__injected__": {
            "predictions": {hash(meta): (45.45, (23.0, 100))},
            "meta_file_path_template": template,
        },
    }


def test_check_levels_predictive_default_render_func() -> None:
    metric_name = "my_test_metric"
    result = next(
        check_levels_predictive(
            42.42,
            metric_name=metric_name,
            levels=_get_test_levels_v1(metric_name, ""),
        )
    )

    assert isinstance(result, Result)
    assert result.summary.startswith("42.42")


def test_check_levels_predictive_prediction_exists(tmpdir: Path) -> None:
    metric_name = "my_test_metric"
    template = str(tmpdir / "testfile")
    _result = next(
        check_levels_predictive(
            42.42,
            metric_name=metric_name,
            levels=_get_test_levels_v1(metric_name, template),
        )
    )

    assert not Path(template).exists()


def test_check_levels_predictive_prediction_not_found(tmpdir: Path) -> None:
    other_metric_name = "my_other_test_metric"
    metric_name = "my_test_metric"
    template = str(tmpdir / "testfile")
    _result = next(
        check_levels_predictive(
            42.42,
            metric_name=other_metric_name,
            levels=_get_test_levels_v1(metric_name, template),
        )
    )

    assert Path(template).exists()
