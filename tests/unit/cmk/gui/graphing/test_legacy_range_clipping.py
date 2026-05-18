#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Regression tests for SUP-28579.
#
# Legacy graph_info entries declare their y-axis range as RPN expressions, e.g.
# graph_info["util_fallback"]["range"] = (0, "util,100,MAX") meaning
# "axis at least 0..100, expand if util goes higher". Before the fix,
# _parse_raw_graph_range produced a FixedGraphTemplateRange whose upper bound
# was evaluated against the *current* scalar value of `util`, so historical
# peaks above the current value were clipped off the y-axis (the original
# customer report shows a container at util=614% with a 783% peak clipped at
# ~614%). The fix parses legacy ranges as MinimalGraphTemplateRange, matching
# the explicit MinimalRange semantics of the 2.4 graphing API and letting
# _compute_min_max expand the axis to fit the actual plotted values.

from cmk.gui.graphing._artwork import (
    _compute_v_axis_min_max,
    LayoutedCurveLine,
)
from cmk.gui.graphing._graph_specification import MinimalVerticalRange
from cmk.gui.graphing._graph_templates import evaluate_graph_template_range
from cmk.gui.graphing._utils import (
    _parse_raw_graph_range,
    MinimalGraphTemplateRange,
    SizeEx,
    translate_metrics,
)
from cmk.gui.type_defs import Perfdata, PerfDataTuple


def test_parse_raw_graph_range_returns_minimal_range() -> None:
    # Legacy ranges must be Minimal so historical peaks are not clipped.
    assert isinstance(
        _parse_raw_graph_range((0, "util,100,MAX")),
        MinimalGraphTemplateRange,
    )


def test_legacy_util_range_does_not_clip_historical_peaks() -> None:
    # End-to-end repro of the customer scenario: util currently 614%, historical
    # peak 783%, graph template range (0, "util,100,MAX"). The y-axis must
    # expand to cover the peak.
    util_current = 614.0
    util_historical_peak = 783.0

    perfdata: Perfdata = [
        PerfDataTuple("util", "util", util_current, "%", None, None, 0, None),
    ]
    translated_metrics = translate_metrics(perfdata, "check_mk-docker_container_cpu")

    explicit_range = evaluate_graph_template_range(
        _parse_raw_graph_range((0, "util,100,MAX")),
        translated_metrics,
    )
    assert isinstance(explicit_range, MinimalVerticalRange)
    assert explicit_range.min == 0
    assert explicit_range.max == util_current  # MAX(614, 100) evaluated at current util

    curves = [
        LayoutedCurveLine(
            color="",
            title="",
            scalars={},
            type="line",
            points=[400.0, util_historical_peak, 700.0, util_current],
        )
    ]

    v_axis = _compute_v_axis_min_max(
        explicit_range,
        curves,
        graph_data_vrange=None,
        mirrored=False,
        height=SizeEx(1),
    )

    # With Minimal semantics, _compute_min_max expands the upper bound to the
    # maximum of the explicit value and the observed time-series max.
    assert v_axis.real_range == (0.0, util_historical_peak)


def test_legacy_range_still_respects_explicit_floor() -> None:
    # Sanity check: when the time-series stays below the explicit floor, the
    # axis still spans the configured 0..100 range (the legacy author's intent).
    floor = 100.0
    perfdata: Perfdata = [
        PerfDataTuple("util", "util", 5.0, "%", None, None, 0, None),
    ]
    translated_metrics = translate_metrics(perfdata, "check_mk-docker_container_cpu")

    explicit_range = evaluate_graph_template_range(
        _parse_raw_graph_range((0, "util,100,MAX")),
        translated_metrics,
    )
    assert isinstance(explicit_range, MinimalVerticalRange)
    assert explicit_range.max == floor  # MAX(5, 100)

    curves = [
        LayoutedCurveLine(
            color="",
            title="",
            scalars={},
            type="line",
            points=[5.0, 10.0, 8.0, 5.0],
        )
    ]

    v_axis = _compute_v_axis_min_max(
        explicit_range,
        curves,
        graph_data_vrange=None,
        mirrored=False,
        height=SizeEx(1),
    )

    assert v_axis.real_range == (0.0, 100.0)
