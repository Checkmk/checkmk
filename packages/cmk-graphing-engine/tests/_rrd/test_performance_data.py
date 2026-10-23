#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.graphing_engine import MetricName, parse_performance_data, PerformanceData

_LOGGER = logging.getLogger(__name__)


def test_a_metric_only_the_rrd_knows_is_read_as_well() -> None:
    parsed = parse_performance_data("used=10B", "check_mk-df", ["temp"], debug=True, logger=_LOGGER)
    assert sorted(parsed.values) == [MetricName("temp"), MetricName("used")]


def test_performance_data_wins_over_what_the_rrd_reports() -> None:
    parsed = parse_performance_data("used=10B", "check_mk-df", ["used"], debug=True, logger=_LOGGER)
    assert parsed.values[MetricName("used")].value == 10.0


def test_parse_performance_data_merges_rrd_only_metrics() -> None:
    # Legacy reads the livestatus "metrics" column too, so a metric present in RRD but absent from
    # the live perf_data string still shows up (as a synthetic value=1 entry, deduplicated).
    parsed = parse_performance_data(
        "live=5", "check_mk-foo", ["live", "rrd_only"], debug=False, logger=_LOGGER
    )
    by_name = {name: value.value for name, value in parsed.values.items()}
    assert by_name == {"live": 5.0, "rrd_only": 1.0}


def test_parse_performance_data_names_a_metric_by_its_rrd_name() -> None:
    parsed = parse_performance_data(
        "'disk read:sda/1'=5", "check_mk-foo", debug=False, logger=_LOGGER
    )
    assert list(parsed.values) == ["disk_read_sda_1"]


def test_performance_data_with_an_unbalanced_quote_is_still_read() -> None:
    parsed = parse_performance_data(
        "days=10 'expires=5", "check-mk-custom!check_ssl_cert", debug=False, logger=_LOGGER
    )
    assert parsed.values == {
        MetricName("days"): PerformanceData(value=10),
        MetricName("expires"): PerformanceData(value=5),
    }


def test_performance_data_with_an_unbalanced_quote_raises_in_debug_mode() -> None:
    with pytest.raises(ValueError, match="No closing quotation"):
        parse_performance_data(
            "days=10 'expires=5", "check-mk-custom!check_ssl_cert", debug=True, logger=_LOGGER
        )
