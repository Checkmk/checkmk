#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

"""Wire-contract tests for the GUI metric-info endpoint backing the Maps SPA.

``metric_info`` is the GUI-side replacement for the daemon's home-grown
graphing reimplementation: it resolves raw perfdata through Checkmk's own
pipeline (``parse_performance_data`` → ``evaluated_metrics`` →
``evaluated_perfometer``). The pipeline itself is covered by the
graphing tests; what we pin here is the SPA wire format built on top of it —
the Perf-O-Meter payload (rows/sides/label/bg_color) and the per-raw-label
metric map (canonical name, title, scale, UnitFormat-shaped unit, series color).
"""

from collections.abc import Mapping, Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api
from cmk.graphing.v1 import perfometers as perfometers_api
from cmk.graphing.v1 import Title
from cmk.graphing.v1 import translations as translations_api
from cmk.gui.graphing import (
    GraphFromAPI,
    parse_metric_from_api,
    PerfometerFromAPI,
    RegisteredMetric,
)
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.maps.gui._metrics import (
    GraphGroup,
    metric_info,
    MetricDisplay,
    MetricInfo,
    MetricUnit,
    MetricUnitPrecision,
)
from cmk.utils.servicename import ServiceName


def _metric(name: str, title: Title, unit: metrics_api.Unit) -> metrics_api.Metric:
    return metrics_api.Metric(
        name=name,
        title=title,
        unit=unit,
        color=metrics_api.Color.GREEN,
    )


_PERCENT = metrics_api.Unit(metrics_api.DecimalNotation("%"), metrics_api.AutoPrecision(2))
_BYTES = metrics_api.Unit(metrics_api.IECNotation("B"), metrics_api.StrictPrecision(1))

# Two views of the same registry, as ``metric_info`` takes them: the plug-in
# objects the evaluation engine builds quantities from, and the parsed display
# semantics the payload reports.
_METRIC_PLUGINS: Mapping[str, metrics_api.Metric] = {
    "mem_used_percent": _metric("mem_used_percent", Title("RAM usage"), _PERCENT),
    "mem_used": _metric("mem_used", Title("RAM used"), _BYTES),
    "if_in_bps": _metric("if_in_bps", Title("Input bandwidth"), _PERCENT),
    "if_out_bps": _metric("if_out_bps", Title("Output bandwidth"), _PERCENT),
}

_REGISTERED_METRICS: Mapping[str, RegisteredMetric] = {
    name: parse_metric_from_api(plugin) for name, plugin in _METRIC_PLUGINS.items()
}

_REGISTERED_PERFOMETERS: Mapping[str, PerfometerFromAPI] = {
    "mem_used_percent": perfometers_api.Perfometer(
        name="mem_used_percent",
        focus_range=perfometers_api.FocusRange(
            perfometers_api.Closed(0), perfometers_api.Closed(100)
        ),
        segments=["mem_used_percent"],
    ),
    "if_bps": perfometers_api.Bidirectional(
        name="if_bps",
        left=perfometers_api.Perfometer(
            name="if_in_bps",
            focus_range=perfometers_api.FocusRange(
                perfometers_api.Closed(0), perfometers_api.Closed(100)
            ),
            segments=["if_in_bps"],
        ),
        right=perfometers_api.Perfometer(
            name="if_out_bps",
            focus_range=perfometers_api.FocusRange(
                perfometers_api.Closed(0), perfometers_api.Closed(100)
            ),
            segments=["if_out_bps"],
        ),
    ),
}


_REGISTERED_GRAPHS: Mapping[str, GraphFromAPI] = {
    "ram_usage": graphs_api.Graph(
        name="ram_usage",
        title=Title("RAM usage graph"),
        compound_lines=["mem_used_percent"],
    ),
    "bandwidth": graphs_api.Bidirectional(
        name="bandwidth",
        title=Title("Bandwidth"),
        upper=graphs_api.Graph(
            name="bandwidth_up", title=Title("Out"), compound_lines=["if_out_bps"]
        ),
        lower=graphs_api.Graph(
            name="bandwidth_down", title=Title("In"), compound_lines=["if_in_bps"]
        ),
    ),
}

# Renames *and* scales, so the payload has to report the raw label as its key,
# the canonical name as ``name`` and the translation factor as ``scale``.
_TRANSLATIONS: Sequence[translations_api.Translation] = (
    translations_api.Translation(
        name="mem_linux",
        check_commands=[translations_api.PassiveCheck("mem_linux")],
        translations={"memused": translations_api.RenameToAndScaleBy("mem_used", 1048576)},
    ),
)

_OBJECT_CONTEXT = (SiteId("heute"), HostName("myhost"), ServiceName("Interface 1"))


def _info(
    perf_data: str,
    check_command: str = "check_mk-mem_linux",
    registered_translations: Sequence[translations_api.Translation] = (),
) -> MetricInfo:
    return metric_info(
        perf_data,
        check_command,
        registered_metrics=_REGISTERED_METRICS,
        registered_metric_plugins=_METRIC_PLUGINS,
        registered_translations=registered_translations,
        registered_perfometers=_REGISTERED_PERFOMETERS,
        temperature_unit=TemperatureUnit.CELSIUS,
        debug=True,
    )


def _info_with_graphs(perf_data: str) -> MetricInfo:
    return metric_info(
        perf_data,
        "check_mk-mem_linux",
        registered_metrics=_REGISTERED_METRICS,
        registered_metric_plugins=_METRIC_PLUGINS,
        registered_translations=(),
        registered_perfometers=_REGISTERED_PERFOMETERS,
        temperature_unit=TemperatureUnit.CELSIUS,
        debug=True,
        registered_graphs=_REGISTERED_GRAPHS,
        object_context=_OBJECT_CONTEXT,
    )


def test_empty_perf_data_yields_empty_payload() -> None:
    assert _info("   ") == MetricInfo(perfometer=None, metrics={})


def test_simple_perfometer_payload(request_context: None) -> None:
    payload = _info("mem_used_percent=42;80;90;0;100")

    perfometer = payload.perfometer
    assert perfometer is not None
    (side,) = perfometer.sides
    assert side is not None
    assert side.title == "RAM usage"
    assert side.pct == pytest.approx(42.0, abs=0.5)
    assert side.label.startswith("42")
    assert perfometer.label.startswith("42")

    rows = perfometer.rows
    assert len(rows) == 1
    # Fill segment plus the theme background filler, summing to the full bar.
    assert sum(seg.pct for seg in rows[0]) == pytest.approx(100.0, abs=0.5)
    bg_color = perfometer.bg_color
    assert any(seg.color == bg_color for seg in rows[0])
    assert any(seg.color != bg_color for seg in rows[0])


def test_bidirectional_sides_are_per_direction(request_context: None) -> None:
    payload = _info("if_in_bps=25;;;0;100 if_out_bps=75;;;0;100")

    perfometer = payload.perfometer
    assert perfometer is not None
    left, right = perfometer.sides
    assert left is not None and right is not None
    assert left.title == "Input bandwidth"
    assert left.pct == pytest.approx(25.0, abs=0.5)
    assert right.title == "Output bandwidth"
    assert right.pct == pytest.approx(75.0, abs=0.5)
    # The visual stack stays the merged single row (both halves squeezed to 50%).
    assert len(perfometer.rows) == 1


def test_no_matching_perfometer_still_resolves_metrics(request_context: None) -> None:
    payload = _info("mem_used=1073741824;;;0;2147483648")

    assert payload.perfometer is None
    assert payload.metrics["mem_used"].name == "mem_used"
    assert payload.metrics["mem_used"].title == "RAM used"


def test_metric_map_wire_shape(request_context: None) -> None:
    metrics = _info("mem_used=5;;;0;100").metrics

    assert metrics["mem_used"] == MetricDisplay(
        name="mem_used",
        title="RAM used",
        scale=1.0,
        unit=MetricUnit(
            notation="iec",
            symbol="B",
            precision=MetricUnitPrecision(type="strict", digits=1),
        ),
        color="#15d1a0",
    )


def test_translated_metric_is_keyed_by_raw_label(request_context: None) -> None:
    metrics = _info("memused=5;;;0;100", registered_translations=_TRANSLATIONS).metrics

    assert metrics["memused"] == MetricDisplay(
        name="mem_used",
        title="RAM used",
        scale=1048576.0,
        unit=MetricUnit(
            notation="iec",
            symbol="B",
            precision=MetricUnitPrecision(type="strict", digits=1),
        ),
        color="#15d1a0",
    )


def test_unregistered_metric_is_omitted(request_context: None) -> None:
    payload = _info("some_exotic_metric=5;;;;")

    assert payload.perfometer is None
    assert payload.metrics == {}


def test_graphs_absent_unless_requested(request_context: None) -> None:
    assert _info("mem_used_percent=42;80;90;0;100").graphs is None


def test_graphs_matching_group(request_context: None) -> None:
    graphs = _info_with_graphs("mem_used_percent=42;80;90;0;100").graphs

    assert graphs == [
        GraphGroup(
            graph_id="ram_usage",
            title="RAM usage graph",
            metrics=["mem_used_percent"],
            mirrored=[],
        )
    ]


def test_graphs_bidirectional_reports_lower_half_as_mirrored(request_context: None) -> None:
    graphs = _info_with_graphs("if_in_bps=25;;;0;100 if_out_bps=75;;;0;100").graphs

    assert graphs == [
        GraphGroup(
            graph_id="bandwidth",
            title="Bandwidth",
            metrics=["if_out_bps", "if_in_bps"],
            mirrored=["if_in_bps"],
        )
    ]


def test_graphs_empty_when_nothing_applies(request_context: None) -> None:
    assert _info_with_graphs("some_exotic_metric=5;;;;").graphs == []
