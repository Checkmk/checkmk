#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.prediction import FixedPredictionUpdater

from cmk.base.api.agent_based import utils
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result


class MockPredictionUpdater:
    def __init__(self, *a: object, **kw: object) -> None:
        return

    def get_predictive_levels(
        self, *a: object, **kw: object
    ) -> tuple[None, tuple[float, float, None, None]]:
        return None, (2.2, 4.2, None, None)


def test_check_levels_predictive_default_render_func() -> None:
    result = next(
        utils.check_levels_predictive(
            42.42,
            metric_name="metric_name",
            levels={
                "period": "wday",
                "horizon": 10,
                "__get_predictive_levels__": FixedPredictionUpdater(
                    None, (2.2, 4.2, None, None)
                ).get_predictive_levels,
            },
        )
    )

    assert isinstance(result, Result)
    assert result.summary.startswith("42.42")
