#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import Counter
from typing import Literal

from cmk.graphing_engine import FALLBACK_UNIT
from cmk.gui.color import parse_color_into_hexrgb
from cmk.gui.graphing._metric_spec import _fallback_metric_spec, MetricSpec


def test_fallback_metric_spec() -> None:
    color_counter: Counter[Literal["metric", "predictive"]] = Counter()
    assert _fallback_metric_spec("nm-openvpn", color_counter) == MetricSpec(
        name="nm-openvpn",
        title="nm-openvpn",
        unit=FALLBACK_UNIT,
        color=parse_color_into_hexrgb("12/a"),
    )
    assert color_counter["metric"] == 1
