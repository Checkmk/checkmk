#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Self

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing_engine import (
    ConsolidationFunction,
    Curve,
    CurveAttributes,
    evaluate_graphs,
    Graph,
    HostName,
    Line,
    metric_display_attributes,
    MetricName,
    PredictionCurveKind,
    PredictionMetric,
    Region,
    RRDMetric,
    ServiceName,
    SiteID,
    TimeRange,
)
from cmk.gui.config import active_config
from cmk.gui.i18n import _, translate_to_current_language

from ._graph_codec import GraphCodec
from ._graph_dispatch import (
    CommonGraphOptions,
    EvaluatedGraphs,
    FetchDataWithDiagnosticsProtocol,
    GraphDispatcher,
)
from ._plugins import registered_translations
from ._prediction_source import Direction, PredictionFetchData

PREDICTION_KIND: Final = "prediction"

_PREDICTION_STEP: Final = 300

_OBSERVED_COLOR: Final = "#2e7eff"
_REFERENCE_COLOR: Final = "#1a1a1a"
_OK_COLOR: Final = "#15d1a0"
_WARNING_COLOR: Final = "#ffd000"
_CRITICAL_COLOR: Final = "#e85c5c"

_REFERENCE_OF_DIRECTION: Final[Sequence[tuple[Direction, PredictionCurveKind]]] = (
    ("upper", PredictionCurveKind.UPPER_REFERENCE),
    ("lower", PredictionCurveKind.LOWER_REFERENCE),
)


def _observed_metric(
    site_id: SiteID, host_name: HostName, service_name: ServiceName, metric_name: MetricName
) -> RRDMetric:
    return RRDMetric(
        site_id=site_id,
        host_name=host_name,
        service_name=service_name,
        metric_name=metric_name,
        consolidation_function=ConsolidationFunction.MAX,
    )


@dataclass(frozen=True, kw_only=True)
class PredictionGraphContext:
    site_id: SiteID
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    period: str
    valid_from: int
    valid_until: int
    directions: Sequence[Direction]

    def curve_of(self, curve_kind: PredictionCurveKind, attributes: CurveAttributes) -> Curve:
        return Curve(
            quantity=PredictionMetric(
                site_id=self.site_id,
                host_name=self.host_name,
                service_name=self.service_name,
                metric_name=self.metric_name,
                period=self.period,
                valid_from=self.valid_from,
                valid_until=self.valid_until,
                curve_kind=curve_kind,
            ),
            attributes=attributes,
        )


def _attributes(title: str, color: str, unit_of: CurveAttributes) -> CurveAttributes:
    return CurveAttributes(title=title, unit=unit_of.unit, color=color)


def _area_title(title: str, direction: Direction, drawn: Sequence[Direction]) -> str:
    if len(drawn) < 2:
        return title
    return (
        _("%(area)s (upper)") % {"area": title}
        if direction == "upper"
        else _("%(area)s (lower)") % {"area": title}
    )


def _level_regions(context: PredictionGraphContext, unit_of: CurveAttributes) -> Sequence[Region]:
    has_upper = "upper" in context.directions
    has_lower = "lower" in context.directions

    def curve(curve_kind: PredictionCurveKind) -> Curve:
        return context.curve_of(curve_kind, _attributes("", _REFERENCE_COLOR, unit_of))

    def zone(lower: Curve | None, upper: Curve | None, title: str, color: str) -> Region:
        return Region(lower=lower, upper=upper, attributes=_attributes(title, color, unit_of))

    def area(title: str, direction: Direction) -> str:
        return _area_title(title, direction, context.directions)

    upper_warning = curve(PredictionCurveKind.UPPER_WARNING) if has_upper else None
    lower_warning = curve(PredictionCurveKind.LOWER_WARNING) if has_lower else None

    regions = []
    if has_upper:
        upper_critical = curve(PredictionCurveKind.UPPER_CRITICAL)
        regions.append(
            zone(upper_critical, None, area(_("Critical area"), "upper"), _CRITICAL_COLOR)
        )
        regions.append(
            zone(upper_warning, upper_critical, area(_("Warning area"), "upper"), _WARNING_COLOR)
        )
    regions.append(zone(lower_warning, upper_warning, _("OK area"), _OK_COLOR))
    if has_lower:
        lower_critical = curve(PredictionCurveKind.LOWER_CRITICAL)
        regions.append(
            zone(lower_critical, lower_warning, area(_("Warning area"), "lower"), _WARNING_COLOR)
        )
        regions.append(
            zone(None, lower_critical, area(_("Critical area"), "lower"), _CRITICAL_COLOR)
        )
    return regions


def _prediction_line(context: PredictionGraphContext, unit_of: CurveAttributes) -> Line | None:
    for direction, reference_kind in _REFERENCE_OF_DIRECTION:
        if direction in context.directions:
            return Line(
                curve=context.curve_of(
                    reference_kind, _attributes(_("Prediction"), _REFERENCE_COLOR, unit_of)
                ),
                inverse=False,
            )
    return None


def build_prediction_graph(
    context: PredictionGraphContext,
    *,
    title: str,
    metrics: Mapping[str, metrics_v1.Metric],
) -> Graph:
    observed = _observed_metric(
        context.site_id, context.host_name, context.service_name, context.metric_name
    )
    display = metric_display_attributes(
        str(context.metric_name), translate_to_current_language, metrics
    )
    observed_curve = Curve(
        quantity=observed,
        attributes=_attributes(display.title, _OBSERVED_COLOR, display),
    )
    return Graph(
        name=f"prediction_{context.metric_name}",
        title=title,
        kind=PREDICTION_KIND,
        regions=list(_level_regions(context, display)),
        lines=[
            *([line] if (line := _prediction_line(context, display)) else []),
            Line(curve=observed_curve, inverse=False),
        ],
    )


def prediction_window_of(graph: Graph) -> TimeRange | None:
    for metric in graph.metrics():
        if isinstance(metric, PredictionMetric):
            return TimeRange(start=metric.valid_from, end=metric.valid_until, step=_PREDICTION_STEP)
    return None


@dataclass(frozen=True)
class _EvaluatePrediction:
    options: CommonGraphOptions
    fetch_data: FetchDataWithDiagnosticsProtocol

    @classmethod
    def make(cls, options: Mapping[str, object]) -> Self:
        return cls(
            CommonGraphOptions.from_request_options(options),
            PredictionFetchData(
                debug=active_config.debug,
                registered_translations=registered_translations(),
            ),
        )

    def __call__(self, graph: Graph) -> EvaluatedGraphs:
        return EvaluatedGraphs(
            graphs=evaluate_graphs(
                consolidation_function=self.options.consolidation_function,
                time_range=prediction_window_of(graph) or self.options.time_range,
                graphs=[graph],
                fetch_data=self.fetch_data,
            ),
            diagnostics=self.fetch_data.diagnostics,
        )


def prediction_graph_dispatcher(codec: GraphCodec) -> GraphDispatcher:
    return GraphDispatcher(
        kind=PREDICTION_KIND,
        codec=codec,
        make_evaluate=_EvaluatePrediction.make,
    )
