#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Metric-registry lookups for the Maps SPA.

The Maps GUI runs in a full Checkmk request context, so it resolves raw
service perfdata against Checkmk's own graphing machinery
(``cmk.gui.graphing``): the check-command metric translations, the registered
display units and titles, and the Perf-O-Meter renderers — the same pipeline
the monitoring views use. The SPA already holds each object's ``perf_data``
and ``check_command`` from the daemon's state stream and posts them here, so
the Flask-free Maps daemon needs no graphing knowledge of its own.

The Perf-O-Meter payload is the renderer's output verbatim: ``rows`` are the
projected segment stacks including the theme background filler (``bg_color``
says which color that is, so the SPA can restyle it), ``label`` is the value
label the views would show. ``sides`` adds what the SPA cannot derive from
the stack — per gauge "side" (one for a plain Perf-O-Meter, upper/lower for
a stacked one, left/right for a bidirectional one) the metric title, the
formatted value label and the utilization percentage, each half projected as
a standalone Perf-O-Meter over its own focus range.

:mod:`cmk.maps.rest_api.internal` maps the dataclasses below onto the wire
models its endpoint publishes.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Literal

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import perfometers as perfometers_v1
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable
from cmk.graphing.v2_unstable import perfometers as perfometers_v2_unstable
from cmk.graphing_engine import (
    build_matched_graphs,
    MetricName,
    Service,
    SiteID,
)
from cmk.graphing_engine import (
    HostName as EngineHostName,
)
from cmk.graphing_engine import (
    ServiceName as EngineServiceName,
)
from cmk.gui.graphing import (
    drawn_segments,
    DrawnSegment,
    evaluated_metrics,
    evaluated_perfometer,
    EvaluatedMetric,
    GraphFromAPI,
    parse_performance_data,
    perfometer_label,
    PerfometerFromAPI,
    RegisteredMetric,
    sort_registered_graph_plugins,
    translated_names_and_scales,
)
from cmk.gui.i18n import translate_to_current_language
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.gui.view_utils import get_themed_perfometer_bg_color
from cmk.utils.servicename import ServiceName


@dataclass(frozen=True, kw_only=True)
class PerfometerSegment:
    pct: float
    color: str


@dataclass(frozen=True, kw_only=True)
class PerfometerSide:
    """Title, value label and utilization of one gauge side."""

    title: str | None
    label: str
    pct: float


@dataclass(frozen=True, kw_only=True)
class Perfometer:
    label: str
    rows: list[list[PerfometerSegment]]
    sides: list[PerfometerSide | None]
    bg_color: str


# Mirrors the ``UnitFormat`` enums in cmk-shared-typing.
NotationType = Literal[
    "decimal", "si", "iec", "standard_scientific", "engineering_scientific", "time"
]
PrecisionType = Literal["auto", "strict"]


@dataclass(frozen=True, kw_only=True)
class MetricUnitPrecision:
    type: PrecisionType
    digits: int


@dataclass(frozen=True, kw_only=True)
class MetricUnit:
    """cmk-shared-typing UnitFormat — the shape the SPA's unit-format library consumes."""

    notation: NotationType
    symbol: str
    precision: MetricUnitPrecision


@dataclass(frozen=True, kw_only=True)
class MetricDisplay:
    """Display semantics of one RAW perfdata label."""

    name: str
    title: str
    # Converts the raw perfdata value into the registry's canonical unit (e.g. ms → s).
    scale: float
    unit: MetricUnit
    # The registry's own series color, so a Maps chart draws the metric in the
    # same colour Checkmk's graphs do.
    color: str


@dataclass(frozen=True, kw_only=True)
class GraphGroup:
    graph_id: str
    title: str
    metrics: list[str]
    mirrored: list[str]


@dataclass(frozen=True, kw_only=True)
class MetricInfo:
    """Everything the SPA needs to render one object's perfdata."""

    perfometer: Perfometer | None
    metrics: dict[str, MetricDisplay]
    # None when the caller did not ask for graph groups (see ``metric_info``).
    graphs: list[GraphGroup] | None = None


_GRAPH_KIND: Final = "template"


@dataclass(frozen=True, kw_only=True)
class _EngineInputs:
    """What Checkmk's Perf-O-Meter evaluation needs besides the perfdata itself.

    Passed in rather than read from the process registries, so the wire
    contract stays testable against fixtures. ``host_name``/``service_name``
    only identify the series the quantities are read from; a Perf-O-Meter
    resolved without an object context (the per-state-tick case) passes the
    empty strings the endpoint defaults to.
    """

    registered_metric_plugins: Mapping[str, metrics_v1.Metric]
    registered_translations: Sequence[translations_v1.Translation]
    host_name: str
    service_name: str
    debug: bool


def _row_fill(row: Sequence[DrawnSegment]) -> float:
    """Utilization of one rendered stack row: everything that is not padding.

    The engine pads a row to its full width with a trailing segment carrying no
    colour of its own; ``color is None`` is what marks it. The wire model still
    paints that filler in the theme colour (see ``bg_color``) so the SPA can
    restyle it, but the share is read off the structure, not off a colour match.
    """
    return round(min(100.0, sum(seg.share for seg in row if seg.color is not None)), 2)


def _first_segment_title(
    side: perfometers_v1.Perfometer | perfometers_v2_unstable.Perfometer,
    metrics: Mapping[MetricName, EvaluatedMetric],
) -> str | None:
    """Title of the side's leading plain-metric segment ("RAM usage", "Input bandwidth")."""
    for segment in side.segments:
        if isinstance(segment, str):
            evaluated = metrics.get(MetricName(segment))
            return evaluated.title if evaluated else None
    return None


def _side_payload(
    side: perfometers_v1.Perfometer | perfometers_v2_unstable.Perfometer,
    perf_data_str: str,
    check_command: str,
    metrics: Mapping[MetricName, EvaluatedMetric],
    engine: _EngineInputs,
    temperature_unit: TemperatureUnit,
) -> PerfometerSide | None:
    """One gauge side, projected as a standalone Perf-O-Meter.

    The merged bidirectional/stacked stack squeezes each half into its own
    row/50% band, so every side is evaluated again on its own — a registry of
    exactly this one Perf-O-Meter — to get its true utilization over the full
    0-100 range, for gauge fills and line endpoints.
    """
    evaluated = evaluated_perfometer(
        perf_data_str,
        check_command,
        host_name=engine.host_name,
        service_name=engine.service_name,
        registered_perfometers={side.name: side},
        registered_metrics=engine.registered_metric_plugins,
        registered_translations=engine.registered_translations,
        debug=engine.debug,
    )
    if evaluated is None or not (rows := drawn_segments(evaluated)):
        return None
    return PerfometerSide(
        title=_first_segment_title(side, metrics),
        label=perfometer_label(evaluated, temperature_unit),
        pct=_row_fill(rows[0]),
    )


def _component_perfometers(
    plugin: PerfometerFromAPI,
) -> Sequence[perfometers_v1.Perfometer | perfometers_v2_unstable.Perfometer]:
    """The plain Perf-O-Meters a plugin is composed of, in stack-row order."""
    if isinstance(plugin, perfometers_v1.Bidirectional | perfometers_v2_unstable.Bidirectional):
        return [plugin.left, plugin.right]
    if isinstance(plugin, perfometers_v1.Stacked | perfometers_v2_unstable.Stacked):
        return [plugin.upper, plugin.lower]
    return [plugin]


def _perfometer_payload(
    perf_data_str: str,
    check_command: str,
    metrics: Mapping[MetricName, EvaluatedMetric],
    registered_perfometers: Mapping[str, PerfometerFromAPI],
    engine: _EngineInputs,
    temperature_unit: TemperatureUnit,
) -> Perfometer | None:
    evaluated = evaluated_perfometer(
        perf_data_str,
        check_command,
        host_name=engine.host_name,
        service_name=engine.service_name,
        registered_perfometers=registered_perfometers,
        registered_metrics=engine.registered_metric_plugins,
        registered_translations=engine.registered_translations,
        debug=engine.debug,
    )
    if evaluated is None or not (rows := drawn_segments(evaluated)):
        return None

    # The engine leaves the trailing padding segment colourless; the wire model
    # paints it in the theme colour and names that colour, so the SPA can swap it.
    bg_color = get_themed_perfometer_bg_color()
    return Perfometer(
        label=perfometer_label(evaluated, temperature_unit),
        rows=[
            [
                PerfometerSegment(
                    pct=round(segment.share, 2),
                    color=bg_color if segment.color is None else segment.color,
                )
                for segment in row
            ]
            for row in rows
        ],
        sides=[
            _side_payload(side, perf_data_str, check_command, metrics, engine, temperature_unit)
            for side in _component_perfometers(registered_perfometers[evaluated.name])
        ],
        bg_color=bg_color,
    )


def _metrics_payload(
    names_and_scales: Mapping[MetricName, tuple[MetricName, float]],
    metrics: Mapping[MetricName, EvaluatedMetric],
    registered_metrics: Mapping[str, RegisteredMetric],
) -> dict[str, MetricDisplay]:
    """Display semantics per RAW perfdata label (what the SPA parses and stores).

    Metrics without a registry entry are omitted — the SPA falls back to its
    own heuristics for those, instead of getting a synthesized fallback spec.

    The unit comes from the registry, not from the evaluated metric: the SPA
    formats the raw perfdata value itself (scaled by ``scale``), so the unit it
    is given must be the registry's own — an evaluated metric carries the unit
    the user's temperature preference converted its values into.
    """
    out: dict[str, MetricDisplay] = {}
    for raw_name, (canonical, scale) in names_and_scales.items():
        registered = registered_metrics.get(canonical)
        evaluated = metrics.get(canonical)
        if registered is None or evaluated is None:
            continue
        unit = registered.unit_spec
        out[raw_name] = MetricDisplay(
            name=canonical,
            title=evaluated.title,
            scale=scale,
            unit=MetricUnit(
                notation=unit.notation.type,
                symbol=unit.notation.symbol,
                precision=MetricUnitPrecision(
                    type=unit.precision.type,
                    digits=unit.precision.digits,
                ),
            ),
            color=evaluated.color,
        )
    return out


def _evaluated_metric_names(
    plugin: GraphFromAPI,
    metrics: Mapping[MetricName, EvaluatedMetric],
    engine: _EngineInputs,
    object_context: tuple[SiteId, HostName, ServiceName],
) -> list[MetricName]:
    """Canonical names of the metrics a graph plugin would actually draw;
    empty when the plugin doesn't apply to these metrics.

    The engine does the matching, against exactly the metrics this perfdata
    resolved to: the SPA already sent us the object's ``perf_data``, so the
    available names are handed over instead of being fetched back out of RRD.
    """
    site_id, host_name, service_name = object_context
    service = Service(
        site_id=SiteID(site_id),
        host_name=EngineHostName(host_name),
        service_name=EngineServiceName(service_name),
    )
    available = frozenset(metrics)
    graphs = build_matched_graphs(
        localizer=translate_to_current_language,
        fetch_metric_names=lambda: {service: available},
        kind=_GRAPH_KIND,
        registered_graphs=[plugin],
        registered_metrics=engine.registered_metric_plugins,
        graph_name=plugin.name,
    )
    return sorted({metric.metric_name for graph in graphs for metric in graph.metrics()})


def _graphs_payload(
    names_and_scales: Mapping[MetricName, tuple[MetricName, float]],
    metrics: Mapping[MetricName, EvaluatedMetric],
    registered_graphs: Mapping[str, GraphFromAPI],
    engine: _EngineInputs,
    object_context: tuple[SiteId, HostName, ServiceName],
) -> list[GraphGroup]:
    """The graph plugins applicable to these metrics, as groups of RAW labels.

    Uses Checkmk's own graph evaluation to decide applicability and which
    metrics each graph draws; a Bidirectional's halves are evaluated
    separately so its lower half is reported as ``mirrored``. Canonical names
    are mapped back to the raw perfdata labels so they line up with the
    series keys the client parses and fetches.
    """
    raw_by_canonical: dict[MetricName, MetricName] = {}
    for raw_name, (canonical, _scale) in names_and_scales.items():
        raw_by_canonical.setdefault(canonical, raw_name)

    def _raw_labels(canonical_names: Sequence[MetricName]) -> list[str]:
        return [str(raw_by_canonical[name]) for name in canonical_names if name in raw_by_canonical]

    groups: list[GraphGroup] = []
    for _name, plugin in sort_registered_graph_plugins(registered_graphs):
        if isinstance(plugin, graphs_v1.Bidirectional | graphs_v2_unstable.Bidirectional):
            upper = _evaluated_metric_names(plugin.upper, metrics, engine, object_context)
            lower = _evaluated_metric_names(plugin.lower, metrics, engine, object_context)
            names = upper + [n for n in lower if n not in upper]
            mirrored = lower
        else:
            names = _evaluated_metric_names(plugin, metrics, engine, object_context)
            mirrored = []
        raw_labels = _raw_labels(names)
        if not raw_labels:
            continue
        groups.append(
            GraphGroup(
                graph_id=plugin.name,
                title=plugin.title.localize(translate_to_current_language),
                metrics=raw_labels,
                mirrored=_raw_labels(mirrored),
            )
        )

    # Several plugins can share a title (edition variants); keep the one
    # drawing the most metrics so the client's graph picker stays free of
    # duplicate rows.
    best: dict[str, GraphGroup] = {}
    for group in groups:
        existing = best.get(group.title)
        if existing is None or len(group.metrics) > len(existing.metrics):
            best[group.title] = group
    return list(best.values())


def object_context(
    site_id: str, host_name: str, service_description: str
) -> tuple[SiteId, HostName, ServiceName]:
    """The object identity the graph evaluation needs, from plain client strings.

    Raises :class:`HostNameValidationError` on a malformed host name — callers
    turn that into their own "invalid input" error. Lives here because only this
    component may name the ``cmk.utils`` service type.
    """
    return (SiteId(site_id), HostName(host_name), ServiceName(service_description))


def metric_info(
    perf_data_str: str,
    check_command: str,
    *,
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_metric_plugins: Mapping[str, metrics_v1.Metric],
    registered_translations: Sequence[translations_v1.Translation],
    registered_perfometers: Mapping[str, PerfometerFromAPI],
    temperature_unit: TemperatureUnit,
    debug: bool,
    registered_graphs: Mapping[str, GraphFromAPI] | None = None,
    object_context: tuple[SiteId, HostName, ServiceName] | None = None,
) -> MetricInfo:
    """Resolve raw perfdata display semantics through Checkmk's graphing pipeline.

    Two views of the metric registry are needed: ``registered_metrics`` carries
    the parsed display semantics this module reports, ``registered_metric_plugins``
    the plug-in objects the evaluation engine builds its quantities from.

    Graph groups are computed only when ``registered_graphs`` and
    ``object_context`` are given — walking every registered graph plugin is
    too costly for the per-state-tick perfometer/unit lookups that don't
    need them.
    """
    if not perf_data_str.strip():
        return MetricInfo(perfometer=None, metrics={})
    raw_performance_data = parse_performance_data(perf_data_str, check_command, debug=debug)
    names_and_scales = translated_names_and_scales(
        raw_performance_data.check_command,
        list(raw_performance_data.values),
        registered_translations,
    )
    metrics = evaluated_metrics(
        perf_data_str,
        check_command,
        registered_metrics=registered_metric_plugins,
        registered_translations=registered_translations,
        temperature_unit=temperature_unit,
        debug=debug,
    )
    _site_id, host_name, service_name = object_context or (None, "", "")
    engine = _EngineInputs(
        registered_metric_plugins=registered_metric_plugins,
        registered_translations=registered_translations,
        host_name=str(host_name),
        service_name=str(service_name),
        debug=debug,
    )
    return MetricInfo(
        perfometer=_perfometer_payload(
            perf_data_str,
            check_command,
            metrics,
            registered_perfometers,
            engine,
            temperature_unit,
        ),
        metrics=_metrics_payload(names_and_scales, metrics, registered_metrics),
        graphs=(
            None
            if registered_graphs is None or object_context is None
            else _graphs_payload(
                names_and_scales, metrics, registered_graphs, engine, object_context
            )
        ),
    )
