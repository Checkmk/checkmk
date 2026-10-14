#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import MetricName
from cmk.gui.graphing import parse_performance_data


def test_a_metric_only_the_rrd_knows_is_read_as_well() -> None:
    parsed = parse_performance_data("used=10B", "check_mk-df", ["temp"], debug=True)
    assert sorted(parsed.values) == [MetricName("temp"), MetricName("used")]


def test_performance_data_wins_over_what_the_rrd_reports() -> None:
    parsed = parse_performance_data("used=10B", "check_mk-df", ["used"], debug=True)
    assert parsed.values[MetricName("used")].value == 10.0
