#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Public interface of the package. By role: the objects for constructing a (data-free) graph
# definition (Graph, Stack, Line, Rule, Curve, the quantities, the ranges, Unit / notations);
# the data objects fed into evaluation (RRDMetricData, TimeSeries, PerformanceData, the
# EvaluationContext, ConsolidationFunction, TimeRange); the evaluation result objects (Evaluated*,
# DiscoveredGraph(s)); and the entry points discovery / evaluation / update build from them
# (build_service_graphs, match_graph_for_services, fetch_performance_data, performance_data_of,
# update_graph_time_series, update_graph_data, metric_display_attributes). Everything else is an
# implementation detail and must not be imported from outside the package.
from ._evaluate import (
    DiscoveredGraph,
    DiscoveredGraphs,
    EvaluatedCurve,
    EvaluatedGraph,
    EvaluatedLine,
    EvaluatedRule,
    EvaluatedStack,
    EvaluatedVerticalRange,
    VerticalRangeKind,
)
from ._fetch import (
    fetch_performance_data,
    performance_data_of,
    RRDSource,
    update_graph_data,
    update_graph_time_series,
)
from ._from_api import metric_display_attributes
from ._objects import (
    AutoPrecision,
    Constant,
    Curve,
    CurveAttributes,
    DecimalNotation,
    Difference,
    EvaluationContext,
    FixedRange,
    Fraction,
    Graph,
    IECNotation,
    Line,
    MetricName,
    MinimalRange,
    PerformanceData,
    PerformanceValue,
    Product,
    Quantity,
    RRDMetric,
    RRDMetricData,
    Rule,
    ScalarKind,
    ScalarOf,
    ServiceRef,
    SINotation,
    Stack,
    StrictPrecision,
    Sum,
    TimeNotation,
    TimeSeries,
    Unit,
    VerticalRange,
)
from ._options import (
    ConsolidationFunction,
    TimeRange,
)
from ._template import (
    build_service_graphs,
    match_graph_for_services,
)

__all__ = [
    "AutoPrecision",
    "ConsolidationFunction",
    "Constant",
    "Curve",
    "CurveAttributes",
    "DecimalNotation",
    "Difference",
    "DiscoveredGraph",
    "DiscoveredGraphs",
    "EvaluatedCurve",
    "EvaluatedGraph",
    "EvaluatedLine",
    "EvaluatedRule",
    "EvaluatedStack",
    "EvaluatedVerticalRange",
    "EvaluationContext",
    "FixedRange",
    "Fraction",
    "Graph",
    "IECNotation",
    "Line",
    "MetricName",
    "MinimalRange",
    "PerformanceData",
    "PerformanceValue",
    "Product",
    "Quantity",
    "RRDMetric",
    "RRDMetricData",
    "RRDSource",
    "Rule",
    "SINotation",
    "ScalarKind",
    "ScalarOf",
    "ServiceRef",
    "Stack",
    "StrictPrecision",
    "Sum",
    "TimeNotation",
    "TimeRange",
    "TimeSeries",
    "Unit",
    "VerticalRange",
    "VerticalRangeKind",
    "build_service_graphs",
    "fetch_performance_data",
    "match_graph_for_services",
    "metric_display_attributes",
    "performance_data_of",
    "update_graph_data",
    "update_graph_time_series",
]
