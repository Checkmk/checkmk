#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.ciena_cpu_util import (
    check_ciena_cpu_util_5142,
    check_ciena_cpu_util_5171,
    Section5171,
)

SECTION_5171 = Section5171(util=12, cores=[("2", 10), ("3", 0)])
SECTION_5142 = 12


@pytest.mark.parametrize(
    "params, result",
    [
        (
            {"util": (0.0, 0.0)},
            [
                Result(state=State.CRIT, summary="Total CPU: 12.00% (warn/crit at 0%/0%)"),
                Metric("util", 12.0, levels=(0.0, 0.0), boundaries=(0.0, None)),
            ],
        ),
        (
            {"util": (80.0, 90.0)},
            [
                Result(state=State.OK, summary="Total CPU: 12.00%"),
                Metric("util", 12.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
            ],
        ),
        (
            {"util": None},
            [
                Result(state=State.OK, summary="Total CPU: 12.00%"),
                Metric("util", 12.0, boundaries=(0.0, None)),
            ],
        ),
        (
            {"util": None, "core_util_graph": True},
            [
                Result(state=State.OK, summary="Total CPU: 12.00%"),
                Metric("util", 12.0, boundaries=(0.0, None)),
                Result(state=State.OK, notice="Core 2: 10.00%"),
                Metric("cpu_core_util_2", 10.0),
                Result(state=State.OK, notice="Core 3: 0%"),
                Metric("cpu_core_util_3", 0.0),
            ],
        ),
    ],
)
def test_check_ciena_cpu_util_5171(params: Mapping[str, object], result: CheckResult) -> None:
    assert list(check_ciena_cpu_util_5171(params, SECTION_5171)) == result


@pytest.mark.parametrize(
    "params, result",
    [
        (
            {"util": (0.0, 0.0)},
            [
                Result(state=State.CRIT, summary="Total CPU: 12.00% (warn/crit at 0%/0%)"),
                Metric("util", 12.0, levels=(0.0, 0.0), boundaries=(0.0, None)),
            ],
        ),
        (
            {"util": (80.0, 90.0)},
            [
                Result(state=State.OK, summary="Total CPU: 12.00%"),
                Metric("util", 12.0, levels=(80.0, 90.0), boundaries=(0.0, None)),
            ],
        ),
        (
            {"util": None},
            [
                Result(state=State.OK, summary="Total CPU: 12.00%"),
                Metric("util", 12.0, boundaries=(0.0, None)),
            ],
        ),
    ],
)
def test_check_ciena_cpu_util_5142(params: Mapping[str, object], result: CheckResult) -> None:
    assert list(check_ciena_cpu_util_5142(params, SECTION_5142)) == result
