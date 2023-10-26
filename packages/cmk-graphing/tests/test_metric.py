#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import Color, Localizable, metric, Unit


def test_metric_error_missing_name() -> None:
    with pytest.raises(AssertionError):
        metric.Metric(
            name="",
            title=Localizable("Title"),
            unit=Unit.COUNT,
            color=Color.BLUE,
        )
