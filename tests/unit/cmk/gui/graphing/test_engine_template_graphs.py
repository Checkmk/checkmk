#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.graphing_engine import (
    AutoPrecision,
    ConsolidationFunction,
    Constant,
    Curve,
    CurveAttributes,
    DecimalNotation,
    Graph,
    HostName,
    Line,
    MetricName,
    PerformanceData,
    PerformanceValue,
    RRDMetric,
    ScalarOf,
    ScalarType,
    ServiceName,
    ServiceRef,
    TimeRange,
    TimeSeries,
    Unit,
)
from cmk.gui.graphing._engine_template_graphs import (
    _assert_uniform_unit,
    build_template_graphs,
    evaluate_template_graphs,
)

_SERVICE = ServiceRef(host_name=HostName("h"), service_name=ServiceName("svc"))
_METRIC = "x"
_DISCOVERY_RANGE = TimeRange(start=0, end=60, step=10)


@dataclass
class _FakeRRD:
    requested_ranges: list[TimeRange] = field(default_factory=list)

    def fetch_performance_data(
        self, services: Sequence[ServiceRef]
    ) -> Mapping[ServiceRef, PerformanceData]:
        return {
            service: PerformanceData(
                check_command="check_mk-foo",
                values=[PerformanceValue(metric_name=MetricName(_METRIC), value=1.0)],
            )
            for service in services
        }

    def fetch_time_series(
        self,
        rrd_metrics: Sequence[RRDMetric],
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
    ) -> Mapping[RRDMetric, TimeSeries]:
        self.requested_ranges.append(time_range)
        return {
            metric: TimeSeries(time_range=time_range, values=[1.0, 1.0, 1.0])
            for metric in rrd_metrics
        }


def test_template_lifecycle_discover_and_update() -> None:
    # Discovery builds the display-resolved graphs (every curve carries its attributes, but no data and no
    # render parameters); the per-type update evaluates them over freshly fetched data for the range it is
    # given. The unclaimed metric becomes a fallback single-metric graph that carries the four threshold
    # rules the engine builds itself.
    rrd = _FakeRRD()
    graphs = build_template_graphs(
        service=_SERVICE,
        rrd=rrd,
        registered_graphs=[],
        registered_metrics={},
        registered_translations=[],
    )
    [fallback] = [graph for graph in graphs if graph.name == _METRIC]
    assert [
        rule.curve.quantity.scalar_type
        for rule in fallback.rules
        if isinstance(rule.curve.quantity, ScalarOf)
    ] == [
        ScalarType.WARNING,
        ScalarType.CRITICAL,
        ScalarType.LOWER_WARNING,
        ScalarType.LOWER_CRITICAL,
    ]
    # Discovery fetches performance data only, never the time series.
    assert rrd.requested_ranges == []

    evaluated = evaluate_template_graphs(
        graphs=graphs,
        consolidation_function=ConsolidationFunction.MAX,
        time_range=_DISCOVERY_RANGE,
        rrd=rrd,
        registered_translations=[],
    )

    assert len(evaluated) == len(graphs)
    # The update fetches the series for the range it is given.
    assert rrd.requested_ranges
    assert all(time_range == _DISCOVERY_RANGE for time_range in rrd.requested_ranges)


def test_discovery_rejects_mixed_units() -> None:
    # A template graph has a single value axis, so curves of different units cannot share it — discovery
    # rejects them (legacy parity). Two curves with distinct intrinsic units trigger the guard without
    # depending on the metric registry.
    bytes_curve = CurveAttributes(
        title="bytes",
        unit=Unit(notation=DecimalNotation("B"), precision=AutoPrecision(2)),
        color="#111111",
    )
    seconds_curve = CurveAttributes(
        title="seconds",
        unit=Unit(notation=DecimalNotation("s"), precision=AutoPrecision(2)),
        color="#222222",
    )
    mixed = Graph(
        name="mixed",
        title="Mixed",
        graph_type="template",
        lines=[
            Line(
                curve=Curve(quantity=Constant(1, bytes_curve), attributes=bytes_curve),
                inverse=False,
            ),
            Line(
                curve=Curve(quantity=Constant(2, seconds_curve), attributes=seconds_curve),
                inverse=False,
            ),
        ],
    )
    with pytest.raises(MKGeneralException, match="different units"):
        _assert_uniform_unit(mixed)
