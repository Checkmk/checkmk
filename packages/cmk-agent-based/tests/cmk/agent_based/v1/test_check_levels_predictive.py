#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Mapping

from cmk.agent_based.v1 import check_levels_predictive, Result

_PredictiveLevels = tuple[
    float | None, tuple[float | None, float | None, float | None, float | None]
]


def _get_test_levels() -> Mapping[str, Callable[[str], _PredictiveLevels]]:
    def get_predictive_levels(_metric: str) -> _PredictiveLevels:
        return None, (2.2, 4.2, None, None)

    return {"__get_predictive_levels__": get_predictive_levels}


def test_check_levels_predictive_default_render_func() -> None:
    result = next(
        check_levels_predictive(
            42.42,
            metric_name="metric_name",
            levels=_get_test_levels(),  # type: ignore[arg-type]
        )
    )

    assert isinstance(result, Result)
    assert result.summary.startswith("42.42")
