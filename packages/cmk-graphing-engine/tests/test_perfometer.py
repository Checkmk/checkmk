#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import perfometers as perfometers_v1
from cmk.graphing.v1 import Title
from cmk.graphing.v2_unstable import metrics as metrics_v2_unstable
from cmk.graphing.v2_unstable import perfometers as perfometers_v2_unstable
from cmk.graphing_engine import (
    AutoPrecision,
    DecimalNotation,
    evaluate_perfometer,
    EvaluatedBidirectional,
    EvaluatedPerfometer,
    EvaluatedPerfometerLayout,
    EvaluatedStacked,
    FocusBoundKind,
    HostName,
    MetricName,
    PerformanceData,
    Service,
    ServiceName,
    Unit,
)

_BLUE = "#28a2f3"
_GRAY = "#8c8c8c"

_SERVICE = Service(host_name=HostName("host"), service_name=ServiceName("svc"))

_METRICS = {
    name: metrics_v1.Metric(
        name=name,
        title=title,
        unit=metrics_v1.Unit(metrics_v1.DecimalNotation("")),
        color=metrics_v1.Color.BLUE,
    )
    for name, title in (
        ("a", Title("Metric a")),
        ("b", Title("Metric b")),
        ("c", Title("Metric c")),
    )
}


def _id(text: str) -> str:
    return text


def _perf(**values: PerformanceData) -> Mapping[MetricName, PerformanceData]:
    return {MetricName(name): data for name, data in values.items()}


def _closed_bar(name: str, *segments: str, upper: float = 100.0) -> perfometers_v1.Perfometer:
    return perfometers_v1.Perfometer(
        name=name,
        focus_range=perfometers_v1.FocusRange(
            perfometers_v1.Closed(0), perfometers_v1.Closed(upper)
        ),
        segments=list(segments),
    )


_MEM_SUPERSEDERS: Mapping[str, str] = {"mem_used": "mem_used_percent"}

type _Plugin = (
    perfometers_v1.Perfometer
    | perfometers_v1.Bidirectional
    | perfometers_v1.Stacked
    | perfometers_v2_unstable.Perfometer
    | perfometers_v2_unstable.Bidirectional
    | perfometers_v2_unstable.Stacked
)


def _registered(*plugins: _Plugin) -> Mapping[str, _Plugin]:
    return {plugin.name: plugin for plugin in plugins}


def _evaluate(
    registered_perfometers: Mapping[str, _Plugin],
    performance_data: Mapping[MetricName, PerformanceData],
    superseders: Mapping[str, str] = {},
) -> EvaluatedPerfometerLayout | None:
    return evaluate_perfometer(
        localizer=_id,
        service=_SERVICE,
        performance_data=performance_data,
        registered_perfometers=registered_perfometers,
        registered_metrics=_METRICS,
        superseders=superseders,
    )


def _drawn_by(
    registered_perfometers: Mapping[str, _Plugin],
    performance_data: Mapping[MetricName, PerformanceData],
    superseders: Mapping[str, str] = {},
) -> str | None:
    evaluated = _evaluate(registered_perfometers, performance_data, superseders)
    return None if evaluated is None else evaluated.name


def test_the_first_matching_plugin_draws() -> None:
    assert (
        _drawn_by(
            _registered(_closed_bar("first", "a"), _closed_bar("second", "a")),
            _perf(a=PerformanceData(value=1.0)),
        )
        == "first"
    )


def test_a_plugin_whose_metric_is_absent_does_not_draw() -> None:
    assert (
        _drawn_by(
            _registered(_closed_bar("wanted_b", "b"), _closed_bar("wanted_a", "a")),
            _perf(a=PerformanceData(value=1.0)),
        )
        == "wanted_a"
    )


def test_a_plugin_whose_scalar_bound_is_absent_does_not_draw() -> None:
    with_scalar = perfometers_v1.Perfometer(
        name="with_scalar",
        focus_range=perfometers_v1.FocusRange(
            perfometers_v1.Closed(0),
            perfometers_v1.Closed(metrics_v1.MaximumOf("a", metrics_v1.Color.BLACK)),
        ),
        segments=["a"],
    )
    registered = _registered(with_scalar, _closed_bar("plain", "a"))
    assert _drawn_by(registered, _perf(a=PerformanceData(value=1.0))) == "plain"
    assert _drawn_by(registered, _perf(a=PerformanceData(value=1.0, maximum=10.0))) == "with_scalar"


def test_a_plugin_whose_bound_metric_is_absent_does_not_draw() -> None:
    with_bound = perfometers_v1.Perfometer(
        name="with_bound",
        focus_range=perfometers_v1.FocusRange(perfometers_v1.Closed(0), perfometers_v1.Closed("b")),
        segments=["a"],
    )
    registered = _registered(with_bound, _closed_bar("plain", "a"))
    assert _drawn_by(registered, _perf(a=PerformanceData(value=1.0))) == "plain"
    assert (
        _drawn_by(registered, _perf(a=PerformanceData(value=1.0), b=PerformanceData(value=10.0)))
        == "with_bound"
    )


def test_a_plugin_reading_no_metric_at_all_never_draws() -> None:
    constant_only = perfometers_v1.Perfometer(
        name="constant_only",
        focus_range=perfometers_v1.FocusRange(perfometers_v1.Closed(0), perfometers_v1.Closed(100)),
        segments=[
            metrics_v1.Constant(
                Title("C"),
                metrics_v1.Unit(metrics_v1.DecimalNotation("")),
                metrics_v1.Color.BLUE,
                5,
            )
        ],
    )
    assert _drawn_by(_registered(constant_only), _perf(a=PerformanceData(value=1.0))) is None


def test_nothing_draws_without_performance_data() -> None:
    assert _drawn_by(_registered(_closed_bar("any", "a")), {}) is None


def test_a_superseder_draws_in_place_of_the_plugin_it_supersedes() -> None:
    registered = _registered(_closed_bar("mem_used", "a"), _closed_bar("mem_used_percent", "b"))
    assert (
        _drawn_by(
            registered,
            _perf(a=PerformanceData(value=1.0), b=PerformanceData(value=2.0)),
            _MEM_SUPERSEDERS,
        )
        == "mem_used_percent"
    )
    assert (
        _drawn_by(registered, _perf(a=PerformanceData(value=1.0)), _MEM_SUPERSEDERS) == "mem_used"
    )


def test_evaluate_a_bar() -> None:
    evaluated = _evaluate(
        _registered(_closed_bar("p", "a", "b")),
        _perf(a=PerformanceData(value=1.0), b=PerformanceData(value=2.0)),
    )
    assert isinstance(evaluated, EvaluatedPerfometer)
    assert evaluated.name == "p"
    assert [segment.value for segment in evaluated.segments] == [1.0, 2.0]
    assert evaluated.focus_range.lower.value == 0.0
    assert evaluated.focus_range.lower.bound_kind is FocusBoundKind.CLOSED
    assert evaluated.focus_range.upper.value == 100.0
    assert evaluated.focus_range.upper.bound_kind is FocusBoundKind.CLOSED


def test_evaluate_carries_the_metric_display_attributes() -> None:
    evaluated = _evaluate(_registered(_closed_bar("p", "a")), _perf(a=PerformanceData(value=1.0)))
    assert isinstance(evaluated, EvaluatedPerfometer)
    (segment,) = evaluated.segments
    assert segment.attributes.title == "Metric a"
    assert segment.attributes.color == _BLUE
    assert segment.attributes.unit == Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))


def test_evaluate_falls_back_for_an_unregistered_metric() -> None:
    evaluated = _evaluate(
        _registered(_closed_bar("p", "unregistered")),
        _perf(unregistered=PerformanceData(value=1.0)),
    )
    assert isinstance(evaluated, EvaluatedPerfometer)
    (segment,) = evaluated.segments
    assert segment.attributes.title == "unregistered"
    assert segment.attributes.color == _GRAY


def test_evaluate_an_open_end() -> None:
    plugin = perfometers_v1.Perfometer(
        name="p",
        focus_range=perfometers_v1.FocusRange(perfometers_v1.Closed(0), perfometers_v1.Open(50)),
        segments=["a"],
    )
    evaluated = _evaluate(_registered(plugin), _perf(a=PerformanceData(value=1.0)))
    assert isinstance(evaluated, EvaluatedPerfometer)
    assert evaluated.focus_range.lower.bound_kind is FocusBoundKind.CLOSED
    assert evaluated.focus_range.upper.bound_kind is FocusBoundKind.OPEN
    assert evaluated.focus_range.upper.value == 50.0


def test_evaluate_a_scalar_bound() -> None:
    plugin = perfometers_v1.Perfometer(
        name="p",
        focus_range=perfometers_v1.FocusRange(
            perfometers_v1.Closed(0),
            perfometers_v1.Closed(metrics_v1.MaximumOf("a", metrics_v1.Color.BLACK)),
        ),
        segments=["a"],
    )
    evaluated = _evaluate(_registered(plugin), _perf(a=PerformanceData(value=1.0, maximum=64.0)))
    assert isinstance(evaluated, EvaluatedPerfometer)
    assert evaluated.focus_range.upper.value == 64.0


def test_evaluate_a_lower_scalar_bound_of_the_unstable_api() -> None:
    plugin = perfometers_v2_unstable.Perfometer(
        name="p",
        focus_range=perfometers_v2_unstable.FocusRange(
            perfometers_v2_unstable.Closed(metrics_v2_unstable.LowerWarningOf("a")),
            perfometers_v2_unstable.Closed(100),
        ),
        segments=["a"],
    )
    evaluated = _evaluate(
        _registered(plugin), _perf(a=PerformanceData(value=1.0, lower_warning=5.0))
    )
    assert isinstance(evaluated, EvaluatedPerfometer)
    assert evaluated.focus_range.lower.value == 5.0


def test_evaluate_an_expression_segment() -> None:
    plugin = perfometers_v1.Perfometer(
        name="p",
        focus_range=perfometers_v1.FocusRange(perfometers_v1.Closed(0), perfometers_v1.Closed(100)),
        segments=[
            metrics_v1.Sum(Title("A plus B"), metrics_v1.Color.RED, ["a", "b"]),
        ],
    )
    evaluated = _evaluate(
        _registered(plugin), _perf(a=PerformanceData(value=1.0), b=PerformanceData(value=2.0))
    )
    assert isinstance(evaluated, EvaluatedPerfometer)
    (segment,) = evaluated.segments
    assert segment.value == 3.0
    assert segment.attributes.title == "A plus B"


def test_evaluate_folds_an_operand_without_a_value() -> None:
    plugin = perfometers_v1.Perfometer(
        name="p",
        focus_range=perfometers_v1.FocusRange(perfometers_v1.Closed(0), perfometers_v1.Closed(100)),
        segments=[
            metrics_v1.Sum(
                Title("A over B plus C"),
                metrics_v1.Color.RED,
                [
                    metrics_v1.Fraction(
                        Title("A over B"),
                        metrics_v1.Unit(metrics_v1.DecimalNotation("")),
                        metrics_v1.Color.RED,
                        dividend="a",
                        divisor="b",
                    ),
                    "c",
                ],
            )
        ],
    )
    evaluated = _evaluate(
        _registered(plugin),
        _perf(
            a=PerformanceData(value=1.0),
            b=PerformanceData(value=0.0),
            c=PerformanceData(value=2.0),
        ),
    )
    assert isinstance(evaluated, EvaluatedPerfometer)
    (segment,) = evaluated.segments
    assert segment.value == 2.0


def test_evaluate_a_bidirectional() -> None:
    plugin = perfometers_v1.Bidirectional(
        name="both",
        left=_closed_bar("l", "a", upper=10.0),
        right=_closed_bar("r", "b", upper=20.0),
    )
    evaluated = _evaluate(
        _registered(plugin), _perf(a=PerformanceData(value=1.0), b=PerformanceData(value=2.0))
    )
    assert isinstance(evaluated, EvaluatedBidirectional)
    assert evaluated.name == "both"
    assert [segment.value for segment in evaluated.left.segments] == [1.0]
    assert evaluated.left.focus_range.upper.value == 10.0
    assert [segment.value for segment in evaluated.right.segments] == [2.0]
    assert evaluated.right.focus_range.upper.value == 20.0


def test_evaluate_a_stacked() -> None:
    plugin = perfometers_v1.Stacked(
        name="two",
        lower=_closed_bar("lo", "a"),
        upper=_closed_bar("up", "b"),
    )
    evaluated = _evaluate(
        _registered(plugin), _perf(a=PerformanceData(value=1.0), b=PerformanceData(value=2.0))
    )
    assert isinstance(evaluated, EvaluatedStacked)
    assert evaluated.name == "two"
    assert [segment.value for segment in evaluated.lower.segments] == [1.0]
    assert [segment.value for segment in evaluated.upper.segments] == [2.0]


def test_evaluate_without_a_matching_plugin() -> None:
    assert (
        _evaluate(_registered(_closed_bar("p", "b")), _perf(a=PerformanceData(value=1.0))) is None
    )


def test_evaluate_a_metric_without_a_value() -> None:
    assert (
        _evaluate(_registered(_closed_bar("p", "a")), _perf(a=PerformanceData(value=None))) is None
    )
