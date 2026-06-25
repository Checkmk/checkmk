#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._engine_rrd_source import EngineRRDSource


def test_parse_performance_data_merges_rrd_only_metrics() -> None:
    # Legacy reads the livestatus "metrics" column too, so a metric present in RRD but absent from
    # the live perf_data string still shows up (as a synthetic value=1 entry, deduplicated).
    parsed = EngineRRDSource.parse_performance_data(
        "live=5", "check_mk-foo", ["live", "rrd_only"], debug=False
    )
    by_name = {value.metric_name: value.value for value in parsed.values}
    assert by_name == {"live": 5.0, "rrd_only": 1.0}
