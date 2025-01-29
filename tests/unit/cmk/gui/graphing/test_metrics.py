#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import Counter
from typing import Literal

from cmk.gui.graphing._color import parse_color_into_hexrgb
from cmk.gui.graphing._formatter import AutoPrecision
from cmk.gui.graphing._metrics import _fallback_metric_spec, _get_legacy_metric_info, MetricSpec
from cmk.gui.graphing._unit import ConvertibleUnitSpecification, DecimalNotation


def test__get_legacy_metric_info() -> None:
    color_counter: Counter[Literal["metric", "predictive"]] = Counter()
    assert _get_legacy_metric_info("foo", Counter()) is None
    assert color_counter["metric"] == 0


def test_fallback_metric_spec() -> None:
    color_counter: Counter[Literal["metric", "predictive"]] = Counter()
    assert _fallback_metric_spec("foo", color_counter) == MetricSpec(
        name="foo",
        title="Foo",
        unit_spec=ConvertibleUnitSpecification(
            notation=DecimalNotation(symbol=""),
            precision=AutoPrecision(digits=2),
        ),
        color=parse_color_into_hexrgb("12/a"),
    )
    assert color_counter["metric"] == 1
