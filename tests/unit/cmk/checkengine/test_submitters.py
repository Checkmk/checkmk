#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.checkengine.checkresults import MetricTuple
from cmk.checkengine.submitters import _serialize_metric


@pytest.mark.parametrize(
    "metric, expected",
    [
        pytest.param(
            MetricTuple(name="m", value=1.0, warn=None, crit=None, min_=None, max_=None),
            "m=1;;;;",
            id="no_levels_no_boundaries",
        ),
        pytest.param(
            MetricTuple(name="m", value=1.0, warn=None, crit=None, min_=0.0, max_=100.0),
            "m=1;;;0;100",
            id="boundaries_only",
        ),
        pytest.param(
            MetricTuple(name="hot_chocolate", value=2.3, warn=None, crit=42.0, min_=0.0, max_=None),
            "hot_chocolate=2.3;;42;0;",
            id="upper_crit_only",
        ),
        pytest.param(
            MetricTuple(name="m", value=5.0, warn=10.0, crit=20.0, min_=None, max_=None),
            "m=5;10;20;;",
            id="upper_levels_only",
        ),
        pytest.param(
            MetricTuple(
                name="x",
                value=5.0,
                warn=10.0,
                crit=20.0,
                min_=None,
                max_=None,
                warn_lower=1.0,
                crit_lower=2.0,
            ),
            "x=5;1:10;2:20;;",
            id="lower_and_upper_levels",
        ),
        pytest.param(
            MetricTuple(
                name="x",
                value=5.0,
                warn=None,
                crit=None,
                min_=None,
                max_=None,
                warn_lower=1.0,
                crit_lower=2.0,
            ),
            "x=5;1:;2:;;",
            id="lower_levels_only",
        ),
    ],
)
def test_serialize_metric(metric: MetricTuple, expected: str) -> None:
    assert _serialize_metric(metric) == expected
