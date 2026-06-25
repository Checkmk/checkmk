#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never

from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable
from cmk.graphing.v2_unstable import metrics as metrics_v2_unstable

from ._objects import (
    AutoPrecision,
    Bound,
    Constant,
    Curve,
    CurveAttributes,
    DecimalNotation,
    Difference,
    EngineeringScientificNotation,
    Fraction,
    IECNotation,
    Line,
    MetricName,
    MetricTranslation,
    MinimalRange,
    Notation,
    Precision,
    Product,
    Quantity,
    ResolvedGraph,
    RRDMetric,
    Rule,
    ScalarKind,
    ScalarOf,
    ServiceRef,
    SINotation,
    Stack,
    StandardScientificNotation,
    StrictPrecision,
    Sum,
    TimeNotation,
    Unit,
)

type _ApiQuantity = (
    str
    | metrics_v1.Constant
    | metrics_v1.WarningOf
    | metrics_v1.CriticalOf
    | metrics_v2_unstable.LowerWarningOf
    | metrics_v2_unstable.LowerCriticalOf
    | metrics_v1.MinimumOf
    | metrics_v1.MaximumOf
    | metrics_v1.Sum
    | metrics_v1.Product
    | metrics_v1.Difference
    | metrics_v1.Fraction
)

_COLORS: dict[metrics_v1.Color, str] = {
    metrics_v1.Color.LIGHT_RED: "#f37c7c",
    metrics_v1.Color.RED: "#ed3b3b",
    metrics_v1.Color.DARK_RED: "#a82a2a",
    metrics_v1.Color.LIGHT_ORANGE: "#ffad54",
    metrics_v1.Color.ORANGE: "#ff8400",
    metrics_v1.Color.DARK_ORANGE: "#b55e00",
    metrics_v1.Color.LIGHT_YELLOW: "#ffe456",
    metrics_v1.Color.YELLOW: "#ffd703",
    metrics_v1.Color.DARK_YELLOW: "#ac7c02",
    metrics_v1.Color.LIGHT_GREEN: "#62e0bf",
    metrics_v1.Color.GREEN: "#15d1a0",
    metrics_v1.Color.DARK_GREEN: "#0f9472",
    metrics_v1.Color.LIGHT_BLUE: "#6fc1f7",
    metrics_v1.Color.BLUE: "#28a2f3",
    metrics_v1.Color.DARK_BLUE: "#1c73ad",
    metrics_v1.Color.LIGHT_CYAN: "#68eeee",
    metrics_v1.Color.CYAN: "#1ee6e6",
    metrics_v1.Color.DARK_CYAN: "#17b5b5",
    metrics_v1.Color.LIGHT_PURPLE: "#acaaff",
    metrics_v1.Color.PURPLE: "#8380ff",
    metrics_v1.Color.DARK_PURPLE: "#5d5bb5",
    metrics_v1.Color.LIGHT_PINK: "#f9a8e2",
    metrics_v1.Color.PINK: "#ec48b6",
    metrics_v1.Color.DARK_PINK: "#be187a",
    metrics_v1.Color.LIGHT_BROWN: "#d4ad84",
    metrics_v1.Color.BROWN: "#bf8548",
    metrics_v1.Color.DARK_BROWN: "#885e33",
    metrics_v1.Color.LIGHT_GRAY: "#acacac",
    metrics_v1.Color.GRAY: "#8c8c8c",
    metrics_v1.Color.DARK_GRAY: "#5d5d5d",
    metrics_v1.Color.BLACK: "#1e262e",
    metrics_v1.Color.WHITE: "#ffffff",
}


def _parse_color(color: metrics_v1.Color) -> str:
    return _COLORS[color]


def _parse_unit(unit: metrics_v1.Unit) -> Unit:
    notation: Notation
    match unit.notation:
        case metrics_v1.DecimalNotation(symbol):
            notation = DecimalNotation(symbol)
        case metrics_v1.SINotation(symbol):
            notation = SINotation(symbol)
        case metrics_v1.IECNotation(symbol):
            notation = IECNotation(symbol)
        case metrics_v1.StandardScientificNotation(symbol):
            notation = StandardScientificNotation(symbol)
        case metrics_v1.EngineeringScientificNotation(symbol):
            notation = EngineeringScientificNotation(symbol)
        case metrics_v1.TimeNotation():
            notation = TimeNotation()
        case _:
            assert_never(unit.notation)

    precision: Precision
    match unit.precision:
        case metrics_v1.AutoPrecision(digits):
            precision = AutoPrecision(digits)
        case metrics_v1.StrictPrecision(digits):
            precision = StrictPrecision(digits)
        case _:
            assert_never(unit.precision)

    return Unit(notation=notation, precision=precision)


_FALLBACK_COLOR = _COLORS[metrics_v1.Color.GRAY]
_FALLBACK_UNIT = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))

# The warn / crit colours threshold rules render in (cf. cmk.gui.color.Color.WARN / .CRIT). They live
# here so resolve_curve can give a scalar rule its label + colour from the ScalarKind, with no GUI input.
_WARN_COLOR = "#ffd000"
_CRIT_COLOR = "#ff3232"
# The English rule label per scalar kind; resolve_curve localizes it. A None colour means "use the
# metric's own colour" (the min / max bound has no warn / crit colour of its own).
_RULE_DISPLAY: Mapping[ScalarKind, tuple[str, str | None]] = {
    ScalarKind.WARNING: ("Warning", _WARN_COLOR),
    ScalarKind.CRITICAL: ("Critical", _CRIT_COLOR),
    ScalarKind.LOWER_WARNING: ("Warning (lower)", _WARN_COLOR),
    ScalarKind.LOWER_CRITICAL: ("Critical (lower)", _CRIT_COLOR),
    ScalarKind.MINIMUM: ("Minimum", None),
    ScalarKind.MAXIMUM: ("Maximum", None),
}


def metric_display_attributes(
    metric_name: str,
    metrics: Mapping[str, metrics_v1.Metric],
    localizer: Callable[[str], str],
) -> CurveAttributes:
    if (definition := metrics.get(metric_name)) is None:
        return CurveAttributes(title=metric_name, unit=_FALLBACK_UNIT, color=_FALLBACK_COLOR)
    return CurveAttributes(
        title=definition.title.localize(localizer),
        unit=_parse_unit(definition.unit),
        color=_parse_color(definition.color),
    )


@dataclass(frozen=True)
class _ParseContext:
    service: ServiceRef
    metrics: Mapping[str, metrics_v1.Metric]
    localizer: Callable[[str], str]

    def rrd_metric(self, metric_name: str) -> RRDMetric:
        return RRDMetric(
            host_name=self.service.host_name,
            service_name=self.service.service_name,
            metric_name=MetricName(metric_name),
        )

    def metric_color(self, metric_name: str) -> str:
        if (definition := self.metrics.get(metric_name)) is None:
            return _FALLBACK_COLOR
        return _parse_color(definition.color)


def _parse_quantity(quantity: _ApiQuantity, context: _ParseContext) -> Quantity:
    # Plain metrics and scalars carry no display — resolve_curve resolves those from the registry / kind.
    # Constants and operations carry their intrinsic plugin display (title / unit / colour), which the
    # registry cannot reproduce, so it is computed here and read back by resolve_curve.
    match quantity:
        case str():
            return context.rrd_metric(quantity)
        case metrics_v1.Constant():
            return Constant(quantity.value, display=_curve_display(quantity, context))
        case metrics_v2_unstable.LowerWarningOf():
            return ScalarOf(
                metric=context.rrd_metric(quantity.metric_name), kind=ScalarKind.LOWER_WARNING
            )
        case metrics_v2_unstable.LowerCriticalOf():
            return ScalarOf(
                metric=context.rrd_metric(quantity.metric_name), kind=ScalarKind.LOWER_CRITICAL
            )
        case metrics_v1.WarningOf():
            return ScalarOf(
                metric=context.rrd_metric(quantity.metric_name), kind=ScalarKind.WARNING
            )
        case metrics_v1.CriticalOf():
            return ScalarOf(
                metric=context.rrd_metric(quantity.metric_name), kind=ScalarKind.CRITICAL
            )
        case metrics_v1.MinimumOf():
            return ScalarOf(
                metric=context.rrd_metric(quantity.metric_name),
                kind=ScalarKind.MINIMUM,
                color=_parse_color(quantity.color),
            )
        case metrics_v1.MaximumOf():
            return ScalarOf(
                metric=context.rrd_metric(quantity.metric_name),
                kind=ScalarKind.MAXIMUM,
                color=_parse_color(quantity.color),
            )
        case metrics_v1.Sum():
            return Sum(
                summands=[_parse_quantity(s, context) for s in quantity.summands],
                display=_curve_display(quantity, context),
            )
        case metrics_v1.Product():
            return Product(
                factors=[_parse_quantity(f, context) for f in quantity.factors],
                display=_curve_display(quantity, context),
            )
        case metrics_v1.Difference():
            return Difference(
                minuend=_parse_quantity(quantity.minuend, context),
                subtrahend=_parse_quantity(quantity.subtrahend, context),
                display=_curve_display(quantity, context),
            )
        case metrics_v1.Fraction():
            return Fraction(
                dividend=_parse_quantity(quantity.dividend, context),
                divisor=_parse_quantity(quantity.divisor, context),
                display=_curve_display(quantity, context),
            )
        case _:
            assert_never(quantity)


def _curve_display(quantity: _ApiQuantity, context: _ParseContext) -> CurveAttributes:
    match quantity:
        case str():
            return metric_display_attributes(quantity, context.metrics, context.localizer)
        case metrics_v1.Constant():
            return CurveAttributes(
                title=quantity.title.localize(context.localizer),
                unit=_parse_unit(quantity.unit),
                color=_parse_color(quantity.color),
            )
        case (
            metrics_v2_unstable.LowerWarningOf()
            | metrics_v2_unstable.LowerCriticalOf()
            | metrics_v1.WarningOf()
            | metrics_v1.CriticalOf()
        ):
            metric = metric_display_attributes(
                quantity.metric_name, context.metrics, context.localizer
            )
            return CurveAttributes(
                title=metric.title,
                unit=metric.unit,
                color=context.metric_color(quantity.metric_name),
            )
        case metrics_v1.MinimumOf() | metrics_v1.MaximumOf():
            metric = metric_display_attributes(
                quantity.metric_name, context.metrics, context.localizer
            )
            return CurveAttributes(
                title=metric.title, unit=metric.unit, color=_parse_color(quantity.color)
            )
        case metrics_v1.Sum():
            return CurveAttributes(
                title=quantity.title.localize(context.localizer),
                unit=_curve_display(quantity.summands[0], context).unit,
                color=_parse_color(quantity.color),
            )
        case metrics_v1.Product():
            return CurveAttributes(
                title=quantity.title.localize(context.localizer),
                unit=_parse_unit(quantity.unit),
                color=_parse_color(quantity.color),
            )
        case metrics_v1.Difference():
            return CurveAttributes(
                title=quantity.title.localize(context.localizer),
                unit=_curve_display(quantity.minuend, context).unit,
                color=_parse_color(quantity.color),
            )
        case metrics_v1.Fraction():
            return CurveAttributes(
                title=quantity.title.localize(context.localizer),
                unit=_parse_unit(quantity.unit),
                color=_parse_color(quantity.color),
            )
        case _:
            assert_never(quantity)


def _metric_names_in_quantity(quantity: _ApiQuantity) -> Iterable[MetricName]:
    match quantity:
        case str():
            yield MetricName(quantity)
        case metrics_v1.Constant():
            return
        case (
            metrics_v2_unstable.LowerWarningOf()
            | metrics_v2_unstable.LowerCriticalOf()
            | metrics_v1.WarningOf()
            | metrics_v1.CriticalOf()
            | metrics_v1.MinimumOf()
            | metrics_v1.MaximumOf()
        ):
            yield MetricName(quantity.metric_name)
        case metrics_v1.Sum():
            for summand in quantity.summands:
                yield from _metric_names_in_quantity(summand)
        case metrics_v1.Product():
            for factor in quantity.factors:
                yield from _metric_names_in_quantity(factor)
        case metrics_v1.Difference():
            yield from _metric_names_in_quantity(quantity.minuend)
            yield from _metric_names_in_quantity(quantity.subtrahend)
        case metrics_v1.Fraction():
            yield from _metric_names_in_quantity(quantity.dividend)
            yield from _metric_names_in_quantity(quantity.divisor)
        case _:
            assert_never(quantity)


def _is_scalar(quantity: _ApiQuantity) -> bool:
    # A scalar quantity (a threshold or constant, possibly combined) is rendered as a horizontal
    # rule, not a drawn curve. Mirrors the legacy _is_scalar split.
    match quantity:
        case str():
            return False
        case (
            metrics_v1.Constant()
            | metrics_v2_unstable.LowerWarningOf()
            | metrics_v2_unstable.LowerCriticalOf()
            | metrics_v1.WarningOf()
            | metrics_v1.CriticalOf()
            | metrics_v1.MinimumOf()
            | metrics_v1.MaximumOf()
        ):
            return True
        case metrics_v1.Sum():
            return all(_is_scalar(s) for s in quantity.summands)
        case metrics_v1.Product():
            return all(_is_scalar(f) for f in quantity.factors)
        case metrics_v1.Difference():
            return _is_scalar(quantity.minuend) and _is_scalar(quantity.subtrahend)
        case metrics_v1.Fraction():
            return _is_scalar(quantity.dividend) and _is_scalar(quantity.divisor)
        case _:
            assert_never(quantity)


def drawn_metric_names_of_graph(
    graph: graphs_v1.Graph | graphs_v2_unstable.Graph,
) -> Sequence[MetricName]:
    # The metrics actually drawn as curves: the non-scalar compound/simple lines. These are what
    # matching requires and what the graph claims. Title references and scalar thresholds are
    # neither required nor claimed — mirroring legacy `_evaluate_graph_lines`, which skips scalars
    # and never consults the title.
    return list(
        {
            name
            for quantity in (*graph.compound_lines, *graph.simple_lines)
            if not _is_scalar(quantity)
            for name in _metric_names_in_quantity(quantity)
        }
    )


def _parse_bound(bound: int | float | _ApiQuantity, context: _ParseContext) -> Bound:
    if isinstance(bound, int | float):
        return bound
    return _parse_quantity(bound, context)


def _parse_minimal_range(
    minimal_range: graphs_v1.MinimalRange | graphs_v2_unstable.MinimalRange,
    context: _ParseContext,
) -> MinimalRange:
    return MinimalRange(
        lower=_parse_bound(minimal_range.lower, context),
        upper=_parse_bound(minimal_range.upper, context),
    )


def _parse_range(
    graph: graphs_v1.Graph | graphs_v2_unstable.Graph,
    context: _ParseContext,
) -> MinimalRange | None:
    return (
        None if graph.minimal_range is None else _parse_minimal_range(graph.minimal_range, context)
    )


def _bidirectional_range(
    graph: graphs_v1.Bidirectional | graphs_v2_unstable.Bidirectional,
    context: _ParseContext,
) -> MinimalRange | None:
    upper = _parse_range(graph.upper, context)
    lower = _parse_range(graph.lower, context)
    if upper is None:
        return lower
    if lower is None:
        return upper
    # The envelope of both halves' ranges (legacy evaluate_graph_plugin_range), not just one half.
    # Numeric bounds combine statically; with a metric-valued bound we cannot, so keep the upper.
    if (
        isinstance(upper.lower, int | float)
        and isinstance(upper.upper, int | float)
        and isinstance(lower.lower, int | float)
        and isinstance(lower.upper, int | float)
    ):
        return MinimalRange(
            lower=min(upper.lower, lower.lower),
            upper=max(upper.upper, lower.upper),
        )
    return upper


def _parse_lines(
    graph: graphs_v1.Graph | graphs_v2_unstable.Graph,
    context: _ParseContext,
    *,
    inverse: bool,
) -> tuple[list[Stack], list[Line], list[Rule]]:
    # Scalar quantities (thresholds/constants) become horizontal rules rather than drawn curves;
    # everything else stacks (compound_lines) or draws as a line (simple_lines). Each drawn quantity is
    # wrapped in a Curve with its display resolved right here (registry / scalar kind / intrinsic).
    def _curve(q: _ApiQuantity) -> Curve:
        return resolve_curve(_parse_quantity(q, context), context.metrics, context.localizer)

    stack_members = [_curve(q) for q in graph.compound_lines if not _is_scalar(q)]
    stacks = [Stack(members=stack_members, inverse=inverse)] if stack_members else []
    lines = [
        Line(curve=_curve(q), inverse=inverse) for q in graph.simple_lines if not _is_scalar(q)
    ]
    rules = [
        Rule(curve=_curve(q), inverse=inverse)
        for q in (*graph.compound_lines, *graph.simple_lines)
        if _is_scalar(q)
    ]
    return stacks, lines, rules


def parse_graph_from_api(
    graph: (
        graphs_v1.Graph
        | graphs_v1.Bidirectional
        | graphs_v2_unstable.Graph
        | graphs_v2_unstable.Bidirectional
    ),
    service: ServiceRef,
    metrics: Mapping[str, metrics_v1.Metric],
    localizer: Callable[[str], str],
    *,
    kind: str,
) -> ResolvedGraph:
    """Build a service's graph from an API plugin, resolving each curve's display inline — discovery
    returns the display-resolved ResolvedGraph directly (no separate structure / resolution step)."""
    context = _ParseContext(
        service=service,
        metrics=metrics,
        localizer=localizer,
    )
    match graph:
        case graphs_v1.Graph() | graphs_v2_unstable.Graph():
            stacks, lines, rules = _parse_lines(graph, context, inverse=False)
            return ResolvedGraph(
                name=graph.name,
                title=graph.title.localize(localizer),
                kind=kind,
                vertical_range=_parse_range(graph, context),
                stacks=stacks,
                lines=lines,
                rules=rules,
            )
        case graphs_v1.Bidirectional() | graphs_v2_unstable.Bidirectional():
            upper_stacks, upper_lines, upper_rules = _parse_lines(
                graph.upper, context, inverse=False
            )
            lower_stacks, lower_lines, lower_rules = _parse_lines(
                graph.lower, context, inverse=True
            )
            return ResolvedGraph(
                name=graph.name,
                title=graph.title.localize(localizer),
                kind=kind,
                vertical_range=_bidirectional_range(graph, context),
                stacks=[*upper_stacks, *lower_stacks],
                lines=[*upper_lines, *lower_lines],
                rules=[*upper_rules, *lower_rules],
            )
        case _:
            assert_never(graph)


def _attributes_for(
    quantity: Quantity,
    metrics: Mapping[str, metrics_v1.Metric],
    localizer: Callable[[str], str],
) -> CurveAttributes:
    """The display of a discovered quantity: plain metrics from the registry, scalar rules from their
    kind, operations / constants from the intrinsic display they carry."""
    match quantity:
        case RRDMetric():
            return metric_display_attributes(quantity.metric_name, metrics, localizer)
        case ScalarOf():
            metric = metric_display_attributes(quantity.metric.metric_name, metrics, localizer)
            label, kind_color = _RULE_DISPLAY[quantity.kind]
            # The author colour (MinimumOf / MaximumOf) wins; otherwise the kind's warn / crit colour;
            # otherwise the metric's own colour.
            return CurveAttributes(
                title=localizer(label),
                unit=metric.unit,
                color=quantity.color or kind_color or metric.color,
            )
        case _:
            # A consumer quantity, resolved generically without the engine knowing its type. Either it
            # delegates its display to a *representative* quantity it exposes via ``display_of`` (e.g. a
            # combined aggregation → its first operand, so the display is resolved fresh from the
            # registry and never cached at discovery — the graph stays purely structural), or it carries
            # its own intrinsic display (an engine operation / constant the registry cannot reproduce).
            if (display_of := getattr(quantity, "display_of", None)) is not None:
                return _attributes_for(display_of(), metrics, localizer)
            display = getattr(quantity, "display", None)
            return (
                display
                if isinstance(display, CurveAttributes)
                else CurveAttributes(title="", unit=_FALLBACK_UNIT, color=_FALLBACK_COLOR)
            )


def resolve_curve(
    quantity: Quantity,
    metrics: Mapping[str, metrics_v1.Metric],
    localizer: Callable[[str], str],
) -> Curve:
    return Curve(quantity=quantity, attributes=_attributes_for(quantity, metrics, localizer))


def _parse_check_command(
    check_command: (
        translations_v1.PassiveCheck
        | translations_v1.ActiveCheck
        | translations_v1.HostCheckCommand
        | translations_v1.NagiosPlugin
    ),
) -> str:
    match check_command:
        case translations_v1.PassiveCheck():
            name = check_command.name
            return name if name.startswith("check_mk-") else f"check_mk-{name}"
        case translations_v1.ActiveCheck():
            name = check_command.name
            return name if name.startswith("check_mk_active-") else f"check_mk_active-{name}"
        case translations_v1.HostCheckCommand():
            name = check_command.name
            return name if name.startswith("check-mk-") else f"check-mk-{name}"
        case translations_v1.NagiosPlugin():
            name = (
                check_command.name
                if check_command.name.startswith("check_")
                else (f"check_{check_command.name}")
            )
            return name.replace(".", "_")
        case _:
            assert_never(check_command)


def _parse_metric_translation(
    old_name: MetricName,
    translation: (
        translations_v1.RenameTo | translations_v1.ScaleBy | translations_v1.RenameToAndScaleBy
    ),
) -> MetricTranslation:
    match translation:
        case translations_v1.RenameTo():
            return MetricTranslation(name=MetricName(translation.metric_name))
        case translations_v1.ScaleBy():
            return MetricTranslation(name=old_name, scale=translation.factor)
        case translations_v1.RenameToAndScaleBy():
            return MetricTranslation(
                name=MetricName(translation.metric_name), scale=translation.factor
            )
        case _:
            assert_never(translation)


def parse_translations_from_api(
    translations: Iterable[translations_v1.Translation],
) -> Mapping[str, Mapping[MetricName, MetricTranslation]]:
    result: dict[str, Mapping[MetricName, MetricTranslation]] = {}
    for translation in translations:
        parsed = {
            MetricName(old_name): _parse_metric_translation(MetricName(old_name), spec)
            for old_name, spec in translation.translations.items()
        }
        for check_command in translation.check_commands:
            result[_parse_check_command(check_command)] = parsed
    return result
