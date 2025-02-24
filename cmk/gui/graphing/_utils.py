#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for main module internals and the plugins"""

import http
import shlex
from collections import Counter, OrderedDict
from collections.abc import Callable, Container, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, NamedTuple, NewType, NotRequired, Self

from typing_extensions import TypedDict

from livestatus import livestatus_lql

import cmk.utils.regex
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.metrics import MetricName
from cmk.utils.plugin_registry import Registry

from cmk.gui import sites
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKHTTPException
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.time_series import TimeSeries, TimeSeriesValue
from cmk.gui.type_defs import Perfdata, PerfDataTuple, Row
from cmk.gui.utils.speaklater import LazyString

from cmk.discover_plugins import DiscoveredPlugins
from cmk.graphing.v1 import graphs, metrics, perfometers, translations

from ._color import get_gray_tone, get_palette_color_by_index, parse_color_into_hexrgb
from ._expression import (
    Constant,
    CriticalOf,
    Difference,
    Fraction,
    Maximum,
    MaximumOf,
    Metric,
    MetricExpression,
    Minimum,
    MinimumOf,
    parse_expression,
    Product,
    Sum,
    WarningOf,
)
from ._loader import graphs_from_api, perfometers_from_api
from ._parser import parse_color, parse_or_add_unit
from ._type_defs import (
    GraphConsoldiationFunction,
    LineType,
    ScalarBounds,
    TranslatedMetric,
    UnitInfo,
)
from ._unit_info import unit_info


class ScalarDefinition(NamedTuple):
    expression: MetricExpression
    title: str


class MetricUnitColor(TypedDict):
    unit: str
    color: str


class MetricDefinition(NamedTuple):
    expression: MetricExpression
    line_type: LineType
    title: str = ""

    def compute_title(self, translated_metrics: Mapping[str, TranslatedMetric]) -> str:
        if self.title:
            return self.title
        return translated_metrics[next(self.expression.metrics()).name]["title"]

    def compute_unit_color(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
        optional_metrics: Sequence[str],
    ) -> MetricUnitColor | None:
        try:
            result = self.expression.evaluate(translated_metrics)
        except KeyError as err:  # because metric_name is not in translated_metrics
            metric_name = err.args[0]
            if optional_metrics and metric_name in optional_metrics:
                return None
            raise MKGeneralException(
                _("Graph recipe '%s' uses undefined metric '%s', available are: %s")
                % (
                    self.expression,
                    metric_name,
                    ", ".join(sorted(translated_metrics.keys())) or "None",
                )
            )
        return MetricUnitColor(unit=result.unit_info["id"], color=result.color)


class MKCombinedGraphLimitExceededError(MKHTTPException):
    status = http.HTTPStatus.BAD_REQUEST


class Curve(TypedDict):
    line_type: LineType | Literal["ref"]
    color: str
    title: str
    rrddata: TimeSeries
    # Added during runtime by _compute_scalars
    scalars: NotRequired[dict[str, tuple[TimeSeriesValue, str]]]


GraphRangeSpec = tuple[int | str, int | str]
SizeEx = NewType("SizeEx", int)


class RawGraphTemplate(TypedDict):
    metrics: Sequence[
        tuple[str, LineType] | tuple[str, LineType, str] | tuple[str, LineType, LazyString]
    ]
    title: NotRequired[str | LazyString]
    scalars: NotRequired[Sequence[str | tuple[str, str | LazyString]]]
    conflicting_metrics: NotRequired[Sequence[str]]
    optional_metrics: NotRequired[Sequence[str]]
    consolidation_function: NotRequired[GraphConsoldiationFunction]
    range: NotRequired[tuple[int | str, int | str]]
    omit_zero_metrics: NotRequired[bool]


def _parse_raw_scalar_definition(
    raw_scalar_definition: str | tuple[str, str | LazyString],
) -> ScalarDefinition:
    if isinstance(raw_scalar_definition, tuple):
        return ScalarDefinition(
            expression=parse_expression(raw_scalar_definition[0], {}),
            title=str(raw_scalar_definition[1]),
        )

    if raw_scalar_definition.endswith(":warn"):
        title = _("Warning")
    elif raw_scalar_definition.endswith(":crit"):
        title = _("Critical")
    else:
        title = raw_scalar_definition
    return ScalarDefinition(
        expression=parse_expression(raw_scalar_definition, {}),
        title=str(title),
    )


def _parse_raw_metric_definition(
    raw_metric_definition: (
        tuple[str, LineType] | tuple[str, LineType, str] | tuple[str, LineType, LazyString]
    ),
) -> MetricDefinition:
    expression, line_type, *title = raw_metric_definition
    return MetricDefinition(
        expression=parse_expression(expression, {}),
        line_type=line_type,
        title=str(title[0]) if title else "",
    )


def _parse_quantity(
    quantity: (
        str
        | metrics.Constant
        | metrics.WarningOf
        | metrics.CriticalOf
        | metrics.MinimumOf
        | metrics.MaximumOf
        | metrics.Sum
        | metrics.Product
        | metrics.Difference
        | metrics.Fraction
    ),
    line_type: Literal["line", "-line", "stack", "-stack"],
) -> MetricDefinition:
    match quantity:
        case str():
            return MetricDefinition(
                expression=Metric(quantity),
                line_type=line_type,
                title=str(get_extended_metric_info(quantity)["title"]),
            )
        case metrics.Constant():
            return MetricDefinition(
                expression=Constant(
                    quantity.value,
                    explicit_unit_name=parse_or_add_unit(quantity.unit)["id"],
                    explicit_color=parse_color(quantity.color),
                ),
                line_type=line_type,
                title=str(quantity.title.localize(_)),
            )
        case metrics.WarningOf():
            metric_ = get_extended_metric_info(quantity.metric_name)
            return MetricDefinition(
                expression=WarningOf(Metric(quantity.metric_name)),
                line_type=line_type,
                title=_("Warning of %s") % metric_["title"],
            )
        case metrics.CriticalOf():
            metric_ = get_extended_metric_info(quantity.metric_name)
            return MetricDefinition(
                expression=CriticalOf(Metric(quantity.metric_name)),
                line_type=line_type,
                title=_("Critical of %s") % metric_["title"],
            )
        case metrics.MinimumOf():
            metric_ = get_extended_metric_info(quantity.metric_name)
            return MetricDefinition(
                expression=MinimumOf(
                    Metric(quantity.metric_name),
                    explicit_color=parse_color(quantity.color),
                ),
                line_type=line_type,
                title=str(metric_["title"]),
            )
        case metrics.MaximumOf():
            metric_ = get_extended_metric_info(quantity.metric_name)
            return MetricDefinition(
                expression=MaximumOf(
                    Metric(quantity.metric_name),
                    explicit_color=parse_color(quantity.color),
                ),
                line_type=line_type,
                title=str(metric_["title"]),
            )
        case metrics.Sum():
            return MetricDefinition(
                expression=Sum(
                    [_parse_quantity(s, line_type).expression for s in quantity.summands],
                    explicit_color=parse_color(quantity.color),
                ),
                line_type=line_type,
                title=str(quantity.title.localize(_)),
            )
        case metrics.Product():
            return MetricDefinition(
                expression=Product(
                    [_parse_quantity(f, line_type).expression for f in quantity.factors],
                    explicit_unit_name=parse_or_add_unit(quantity.unit)["id"],
                    explicit_color=parse_color(quantity.color),
                ),
                line_type=line_type,
                title=str(quantity.title.localize(_)),
            )
        case metrics.Difference():
            return MetricDefinition(
                expression=Difference(
                    minuend=_parse_quantity(quantity.minuend, line_type).expression,
                    subtrahend=_parse_quantity(quantity.subtrahend, line_type).expression,
                    explicit_color=parse_color(quantity.color),
                ),
                line_type=line_type,
                title=str(quantity.title.localize(_)),
            )
        case metrics.Fraction():
            return MetricDefinition(
                expression=Fraction(
                    dividend=_parse_quantity(quantity.dividend, line_type).expression,
                    divisor=_parse_quantity(quantity.divisor, line_type).expression,
                    explicit_unit_name=parse_or_add_unit(quantity.unit)["id"],
                    explicit_color=parse_color(quantity.color),
                ),
                line_type=line_type,
                title=str(quantity.title.localize(_)),
            )


@dataclass(frozen=True, kw_only=True)
class FixedGraphTemplateRange:
    min: MetricExpression
    max: MetricExpression


@dataclass(frozen=True, kw_only=True)
class MinimalGraphTemplateRange:
    min: MetricExpression
    max: MetricExpression


@dataclass(frozen=True)
class GraphTemplate:
    id: str
    title: str | None
    scalars: Sequence[ScalarDefinition]
    conflicting_metrics: Sequence[str]
    optional_metrics: Sequence[str]
    consolidation_function: GraphConsoldiationFunction | None
    range: FixedGraphTemplateRange | MinimalGraphTemplateRange | None
    omit_zero_metrics: bool
    metrics: Sequence[MetricDefinition]

    @classmethod
    def from_name(cls, name: str) -> Self:
        if name.startswith("METRIC_"):
            name = name[7:]
        return cls(
            id=f"METRIC_{name}",
            title=None,
            metrics=[
                MetricDefinition(
                    expression=Metric(name),
                    line_type="area",
                ),
            ],
            scalars=[
                ScalarDefinition(
                    expression=WarningOf(Metric(name)),
                    title=str(_("Warning")),
                ),
                ScalarDefinition(
                    expression=CriticalOf(Metric(name)),
                    title=str(_("Critical")),
                ),
            ],
            conflicting_metrics=[],
            optional_metrics=[],
            consolidation_function=None,
            range=None,
            omit_zero_metrics=False,
        )

    @classmethod
    def from_template(cls, ident: str, template: RawGraphTemplate) -> Self:
        return cls(
            id=ident,
            title=str(template["title"]) if "title" in template else None,
            scalars=[_parse_raw_scalar_definition(r) for r in template.get("scalars", [])],
            conflicting_metrics=template.get("conflicting_metrics", []),
            optional_metrics=template.get("optional_metrics", []),
            consolidation_function=template.get("consolidation_function"),
            range=(
                _parse_raw_graph_range(raw_range) if (raw_range := template.get("range")) else None
            ),
            omit_zero_metrics=template.get("omit_zero_metrics", False),
            metrics=[_parse_raw_metric_definition(r) for r in template["metrics"]],
        )

    @classmethod
    def from_graph(cls, graph: graphs.Graph) -> Self:
        metrics_ = [_parse_quantity(l, "stack") for l in graph.compound_lines]
        scalars: list[ScalarDefinition] = []
        for line in graph.simple_lines:
            match line:
                case (
                    metrics.WarningOf()
                    | metrics.CriticalOf()
                    | metrics.MinimumOf()
                    | metrics.MaximumOf()
                ):
                    parsed = _parse_quantity(line, "line")
                    scalars.append(ScalarDefinition(parsed.expression, parsed.title))
                case _:
                    metrics_.append(_parse_quantity(line, "line"))
        return cls(
            id=graph.name,
            title=graph.title.localize(_),
            range=(
                None if graph.minimal_range is None else _parse_minimal_range(graph.minimal_range)
            ),
            metrics=metrics_,
            scalars=list(scalars),
            optional_metrics=graph.optional,
            conflicting_metrics=graph.conflicting,
            consolidation_function=None,
            omit_zero_metrics=False,
        )

    @classmethod
    def from_bidirectional(cls, graph: graphs.Bidirectional) -> Self:
        ranges_min = []
        ranges_max = []
        if graph.upper.minimal_range is not None:
            upper_range = _parse_minimal_range(graph.upper.minimal_range)
            ranges_min.append(upper_range.min)
            ranges_max.append(upper_range.max)
        if graph.lower.minimal_range is not None:
            lower_range = _parse_minimal_range(graph.lower.minimal_range)
            ranges_min.append(lower_range.min)
            ranges_max.append(lower_range.max)

        metrics_ = [_parse_quantity(l, "stack") for l in graph.upper.compound_lines] + [
            _parse_quantity(l, "-stack") for l in graph.lower.compound_lines
        ]
        scalars: list[ScalarDefinition] = []
        for line in graph.upper.simple_lines:
            match line:
                case (
                    metrics.WarningOf()
                    | metrics.CriticalOf()
                    | metrics.MinimumOf()
                    | metrics.MaximumOf()
                ):
                    parsed = _parse_quantity(line, "line")
                    scalars.append(ScalarDefinition(parsed.expression, parsed.title))
                case _:
                    metrics_.append(_parse_quantity(line, "line"))
        for line in graph.lower.simple_lines:
            match line:
                case (
                    metrics.WarningOf()
                    | metrics.CriticalOf()
                    | metrics.MinimumOf()
                    | metrics.MaximumOf()
                ):
                    parsed = _parse_quantity(line, "-line")
                    scalars.append(ScalarDefinition(parsed.expression, parsed.title))
                case _:
                    metrics_.append(_parse_quantity(line, "-line"))
        return cls(
            id=graph.name,
            title=graph.title.localize(_),
            range=(
                MinimalGraphTemplateRange(
                    min=Minimum(ranges_min),
                    max=Maximum(ranges_max),
                )
                if ranges_min and ranges_max
                else None
            ),
            metrics=metrics_,
            scalars=scalars,
            optional_metrics=list(graph.lower.optional) + list(graph.upper.optional),
            conflicting_metrics=list(graph.lower.conflicting) + list(graph.upper.conflicting),
            consolidation_function=None,
            omit_zero_metrics=False,
        )


def _parse_raw_graph_range(
    raw_graph_range: tuple[int | str, int | str],
) -> FixedGraphTemplateRange:
    return FixedGraphTemplateRange(
        min=parse_expression(raw_graph_range[0], {}),
        max=parse_expression(raw_graph_range[1], {}),
    )


def _parse_minimal_range(
    minimal_range: graphs.MinimalRange,
) -> MinimalGraphTemplateRange:
    return MinimalGraphTemplateRange(
        min=(
            Constant(minimal_range.lower)
            if isinstance(minimal_range.lower, (int, float))
            else _parse_quantity(minimal_range.lower, "line").expression
        ),
        max=(
            Constant(minimal_range.upper)
            if isinstance(minimal_range.upper, (int, float))
            else _parse_quantity(minimal_range.upper, "line").expression
        ),
    )


class CheckMetricEntry(TypedDict, total=False):
    scale: float
    name: MetricName
    auto_graph: bool
    deprecated: str


class _MetricInfoMandatory(TypedDict):
    title: str | LazyString
    unit: str
    color: str


class MetricInfo(_MetricInfoMandatory, total=False):
    help: str | LazyString
    render: Callable[[float | int], str]


class _MetricInfoExtendedMandatory(TypedDict):
    name: MetricName
    title: str | LazyString
    unit: UnitInfo
    color: str


class MetricInfoExtended(_MetricInfoExtendedMandatory, total=False):
    # this is identical to MetricInfo except unit, but one can not override the
    # type of a field so we have to copy everything from MetricInfo
    help: str | LazyString
    render: Callable[[float | int], str]


class _NormalizedPerfData(TypedDict):
    orig_name: list[str]
    value: float
    scalar: ScalarBounds
    scale: list[float]
    auto_graph: bool


class TranslationInfo(TypedDict):
    name: str
    scale: float
    auto_graph: bool


class AutomaticDict(OrderedDict[str, RawGraphTemplate]):
    """Dictionary class with the ability of appending items like provided
    by a list."""

    def __init__(self, list_identifier: str | None = None, start_index: int | None = None) -> None:
        super().__init__(self)
        self._list_identifier = list_identifier or "item"
        self._item_index = start_index or 0

    def append(self, item: RawGraphTemplate) -> None:
        # Avoid duplicate graph definitions in case the metric plug-ins are loaded multiple times.
        # Otherwise, we get duplicate graphs in the UI.
        if self._item_already_appended(item):
            return
        self["%s_%i" % (self._list_identifier, self._item_index)] = item
        self._item_index += 1

    def _item_already_appended(self, item: RawGraphTemplate) -> bool:
        return item in [
            graph_template
            for graph_template_id, graph_template in self.items()
            if graph_template_id.startswith(self._list_identifier)
        ]


metric_info: dict[MetricName, MetricInfo] = {}


class MetricsFromAPI(Registry[MetricInfoExtended]):
    def plugin_name(self, instance: MetricInfoExtended) -> str:
        return instance["name"]


metrics_from_api = MetricsFromAPI()


def registered_metrics() -> Iterator[tuple[str, str]]:
    for metric_id, mie in metrics_from_api.items():
        yield metric_id, str(mie["title"])
    for metric_id, mi in metric_info.items():
        yield metric_id, str(mi["title"])


check_metrics: dict[str, dict[MetricName, CheckMetricEntry]] = {}
# _AutomaticDict is used here to provide some list methods.
# This is needed to maintain backwards-compatibility.
graph_info = AutomaticDict("manual_graph_template")


def _parse_check_command_from_api(
    check_command: (
        translations.PassiveCheck
        | translations.ActiveCheck
        | translations.HostCheckCommand
        | translations.NagiosPlugin
    ),
) -> str:
    match check_command:
        case translations.PassiveCheck():
            return (
                check_command.name
                if check_command.name.startswith("check_mk-")
                else f"check_mk-{check_command.name}"
            )
        case translations.ActiveCheck():
            return (
                check_command.name
                if check_command.name.startswith("check_mk_active-")
                else f"check_mk_active-{check_command.name}"
            )
        case translations.HostCheckCommand():
            return (
                check_command.name
                if check_command.name.startswith("check-mk-")
                else f"check-mk-{check_command.name}"
            )
        case translations.NagiosPlugin():
            return (
                check_command.name
                if check_command.name.startswith("check_")
                else f"check_{check_command.name}"
            )


def _parse_translation(
    translation: translations.RenameTo | translations.ScaleBy | translations.RenameToAndScaleBy,
) -> CheckMetricEntry:
    match translation:
        case translations.RenameTo():
            return {"name": translation.metric_name}
        case translations.ScaleBy():
            return {"scale": translation.factor}
        case translations.RenameToAndScaleBy():
            return {"name": translation.metric_name, "scale": translation.factor}


def add_graphing_plugins(
    plugins: DiscoveredPlugins[
        metrics.Metric
        | translations.Translation
        | perfometers.Perfometer
        | perfometers.Bidirectional
        | perfometers.Stacked
        | graphs.Graph
        | graphs.Bidirectional
    ],
) -> None:
    # TODO CMK-15246 Checkmk 2.4: Remove legacy objects
    for plugin in plugins.plugins.values():
        if isinstance(plugin, metrics.Metric):
            metrics_from_api.register(
                MetricInfoExtended(
                    name=plugin.name,
                    title=plugin.title.localize(_),
                    unit=parse_or_add_unit(plugin.unit),
                    color=parse_color(plugin.color),
                )
            )

        elif isinstance(plugin, translations.Translation):
            for check_command in plugin.check_commands:
                check_metrics[_parse_check_command_from_api(check_command)] = {
                    MetricName(old_name): _parse_translation(translation)
                    for old_name, translation in plugin.translations.items()
                }

        elif isinstance(
            plugin,
            (perfometers.Perfometer, perfometers.Bidirectional, perfometers.Stacked),
        ):
            perfometers_from_api.register(plugin)

        elif isinstance(plugin, (graphs.Graph, graphs.Bidirectional)):
            graphs_from_api.register(plugin)


# .
#   .--Constants-----------------------------------------------------------.
#   |              ____                _              _                    |
#   |             / ___|___  _ __  ___| |_ __ _ _ __ | |_ ___              |
#   |            | |   / _ \| '_ \/ __| __/ _` | '_ \| __/ __|             |
#   |            | |__| (_) | | | \__ \ || (_| | | | | |_\__ \             |
#   |             \____\___/|_| |_|___/\__\__,_|_| |_|\__|___/             |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Various constants to be used by the declarations of the plugins.    |
#   '----------------------------------------------------------------------'
# TODO: Refactor to some namespace object

KB = 1024
MB = KB * 1024
GB = MB * 1024
TB = GB * 1024
PB = TB * 1024

m = 0.001
K = 1000
M = K * 1000
G = M * 1000
T = G * 1000
P = T * 1000

scale_symbols = {
    m: "m",
    1: "",
    KB: "k",
    MB: "M",
    GB: "G",
    TB: "T",
    PB: "P",
    K: "k",
    M: "M",
    G: "G",
    T: "T",
    P: "P",
}


def _parse_perf_values(
    data_str: str,
) -> tuple[str, str, tuple[str | None, str | None, str | None, str | None]]:
    "convert perf str into a tuple with values"
    varname, values = data_str.split("=", 1)
    varname = cmk.utils.pnp_cleanup(varname.replace('"', "").replace("'", ""))

    value_parts = values.split(";")
    value = value_parts.pop(0)

    # Optional warn, crit, min, max fields
    num_fields = len(value_parts)
    other_parts = (
        value_parts[0] if num_fields > 0 else None,
        value_parts[1] if num_fields > 1 else None,
        value_parts[2] if num_fields > 2 else None,
        value_parts[3] if num_fields > 3 else None,
    )

    return varname, value, other_parts


def _split_unit(value_text: str) -> tuple[float | None, str | None]:
    "separate value from unit"

    if not value_text.strip():
        return None, None

    def digit_unit_split(value_text: str) -> int:
        for i, char in enumerate(value_text):
            if char not in "0123456789.,-":
                return i
        return len(value_text)

    cut_unit = digit_unit_split(value_text)

    unit_name = value_text[cut_unit:]
    if value_text[:cut_unit]:
        return _float_or_int(value_text[:cut_unit]), unit_name

    return None, unit_name


def _compute_lookup_metric_name(metric_name: str) -> str:
    if metric_name.startswith("predict_lower_"):
        return metric_name[14:]
    if metric_name.startswith("predict_"):
        return metric_name[8:]
    return metric_name


def _parse_check_command(check_command: str) -> str:
    # This function handles very special and known cases.
    parts = check_command.split("!", 1)
    if parts[0] == "check-mk-custom" and len(parts) >= 2:
        # re.search(r"(^|/)check_ping(\s|$)", parts[1]) would be better..
        if parts[1].startswith("check_ping") or "/check_ping" in parts[1]:
            return "check_ping"
    return parts[0]


def parse_perf_data(
    perf_data_string: str, check_command: str | None = None
) -> tuple[Perfdata, str]:
    """Convert perf_data_string into perf_data, extract check_command"""
    # Strip away arguments like in "check_http!-H checkmk.com"
    if check_command is None:
        check_command = ""
    elif hasattr(check_command, "split"):
        check_command = _parse_check_command(check_command)

    # Split the perf data string into parts. Preserve quoted strings!
    parts = _split_perf_data(perf_data_string)

    # Try if check command is appended to performance data
    # in a PNP like style
    if parts and parts[-1].startswith("[") and parts[-1].endswith("]"):
        check_command = parts[-1][1:-1]
        del parts[-1]

    check_command = check_command.replace(".", "_")  # see function maincheckify

    # Parse performance data, at least try
    perf_data: Perfdata = []

    for part in parts:
        try:
            varname, value_text, value_parts = _parse_perf_values(part)

            value, unit_name = _split_unit(value_text)
            if value is None or unit_name is None:
                continue  # ignore useless empty variable

            perf_data.append(
                PerfDataTuple(
                    varname,
                    _compute_lookup_metric_name(varname),
                    value,
                    unit_name,
                    _float_or_int(value_parts[0]),
                    _float_or_int(value_parts[1]),
                    _float_or_int(value_parts[2]),
                    _float_or_int(value_parts[3]),
                )
            )
        except Exception as exc:
            logger.exception("Failed to parse perfdata '%s'", perf_data_string)
            if active_config.debug:
                raise exc

    return perf_data, check_command


def parse_perf_data_from_performance_data_livestatus_column(
    perf_data_mapping: Mapping[str, float], check_command: str | None = None
) -> tuple[Perfdata, str]:
    """Convert new_perf_data into perf_data"""
    # Strip away arguments like in "check_http!-H checkmk.com"
    if check_command is None:
        check_command = ""
    elif hasattr(check_command, "split"):
        check_command = check_command.split("!")[0]

    check_command = check_command.replace(".", "_")  # see function maincheckify

    perf_data: Perfdata = [
        PerfDataTuple(
            varname,
            _compute_lookup_metric_name(varname),
            value,
            "",
            None,
            None,
            None,
            None,
        )
        for varname, value in perf_data_mapping.items()
    ]

    return perf_data, check_command


def _float_or_int(val: str | None) -> int | float | None:
    """ "45.0" -> 45.0, "45" -> 45"""
    if val is None:
        return None

    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return None


def _split_perf_data(perf_data_string: str) -> list[str]:
    """Split the perf data string into parts. Preserve quoted strings!"""
    return shlex.split(perf_data_string)


def perfvar_translation(
    perfvar_name: str,
    check_command: str | None,  # None due to CMK-13883
) -> TranslationInfo:
    """Get translation info for one performance var."""
    translation_entry = find_matching_translation(
        MetricName(perfvar_name),
        lookup_metric_translations_for_check_command(check_metrics, check_command) or {},
    )
    return TranslationInfo(
        name=translation_entry.get("name", perfvar_name),
        scale=translation_entry.get("scale", 1.0),
        auto_graph=translation_entry.get("auto_graph", True),
    )


def lookup_metric_translations_for_check_command(
    all_translations: Mapping[str, Mapping[MetricName, CheckMetricEntry]],
    check_command: str | None,  # None due to CMK-13883
) -> Mapping[MetricName, CheckMetricEntry] | None:
    if not check_command:
        return None
    return all_translations.get(
        check_command,
        (
            all_translations.get(
                check_command.replace(
                    "check_mk-mgmt_",
                    "check_mk-",
                    1,
                )
            )
            if check_command.startswith("check_mk-mgmt_")
            else None
        ),
    )


def find_matching_translation(
    metric_name: MetricName,
    translations_: Mapping[MetricName, CheckMetricEntry],
) -> CheckMetricEntry:
    if translation := translations_.get(metric_name):
        return translation
    for orig_metric_name, translation in translations_.items():
        if orig_metric_name.startswith("~") and cmk.utils.regex.regex(orig_metric_name[1:]).match(
            metric_name
        ):  # Regex entry
            return translation
    return {}


def _scalar_bounds(perf_data_tuple: PerfDataTuple, scale: float) -> ScalarBounds:
    """rescale "warn, crit, min, max" PERFVAR_BOUNDS values

    Return "None" entries if no performance data and hence no scalars are available
    """
    scalars: ScalarBounds = {}
    if perf_data_tuple.warn is not None:
        scalars["warn"] = float(perf_data_tuple.warn) * scale
    if perf_data_tuple.crit is not None:
        scalars["crit"] = float(perf_data_tuple.crit) * scale
    if perf_data_tuple.min is not None:
        scalars["min"] = float(perf_data_tuple.min) * scale
    if perf_data_tuple.max is not None:
        scalars["max"] = float(perf_data_tuple.max) * scale
    return scalars


def _normalize_perf_data(
    perf_data_tuple: PerfDataTuple, check_command: str
) -> tuple[str, _NormalizedPerfData]:
    translation_entry = perfvar_translation(perf_data_tuple.lookup_metric_name, check_command)

    new_entry = _NormalizedPerfData(
        orig_name=[perf_data_tuple.metric_name],
        value=perf_data_tuple.value * translation_entry["scale"],
        scalar=_scalar_bounds(perf_data_tuple, translation_entry["scale"]),
        scale=[translation_entry["scale"]],  # needed for graph recipes
        # Do not create graphs for ungraphed metrics if listed here
        auto_graph=translation_entry["auto_graph"],
    )

    if perf_data_tuple.metric_name.startswith("predict_lower_"):
        return f"predict_lower_{translation_entry['name']}", new_entry
    if perf_data_tuple.metric_name.startswith("predict_"):
        return f"predict_{translation_entry['name']}", new_entry
    return translation_entry["name"], new_entry


def _get_legacy_metric_info(
    metric_name: str, color_counter: Counter[Literal["metric", "predictive"]]
) -> MetricInfo:
    if metric_name in metric_info:
        return metric_info[metric_name]
    color_counter.update({"metric": 1})
    return MetricInfo(
        title=metric_name.title(),
        unit="",
        color=get_palette_color_by_index(color_counter["metric"]),
    )


def _get_extended_metric_info(
    metric_name: str, color_counter: Counter[Literal["metric", "predictive"]]
) -> MetricInfoExtended:
    if metric_name.startswith("predict_lower_"):
        if (lookup_metric_name := metric_name[14:]) in metrics_from_api:
            mfa = metrics_from_api[lookup_metric_name]
            return MetricInfoExtended(
                name=metric_name,
                title=_("Prediction of ") + mfa["title"] + _(" (lower levels)"),
                unit=mfa["unit"],
                color=get_gray_tone(color_counter),
            )

        mi_ = _get_legacy_metric_info(lookup_metric_name, color_counter)
        mi = MetricInfo(
            title=_("Prediction of ") + mi_["title"] + _(" (lower levels)"),
            unit=mi_["unit"],
            color=get_gray_tone(color_counter),
        )
    elif metric_name.startswith("predict_"):
        if (lookup_metric_name := metric_name[8:]) in metrics_from_api:
            mfa = metrics_from_api[lookup_metric_name]
            return MetricInfoExtended(
                name=metric_name,
                title=_("Prediction of ") + mfa["title"] + _(" (upper levels)"),
                unit=mfa["unit"],
                color=get_gray_tone(color_counter),
            )

        mi_ = _get_legacy_metric_info(lookup_metric_name, color_counter)
        mi = MetricInfo(
            title=_("Prediction of ") + mi_["title"] + _(" (upper levels)"),
            unit=mi_["unit"],
            color=get_gray_tone(color_counter),
        )
    elif metric_name in metrics_from_api:
        return metrics_from_api[metric_name]
    else:
        mi = _get_legacy_metric_info(metric_name, color_counter)

    mie = MetricInfoExtended(
        name=metric_name,
        title=mi["title"],
        unit=unit_info[mi["unit"]],
        color=parse_color_into_hexrgb(mi["color"]),
    )
    if "help" in mi:
        mie["help"] = mi["help"]
    if "render" in mi:
        mie["render"] = mi["render"]

    return mie


def get_extended_metric_info(metric_name: str) -> MetricInfoExtended:
    return _get_extended_metric_info(metric_name, Counter())


def _translated_metric_scalar(
    unit_conversion: Callable[[float], float], scalar_bounds: ScalarBounds
) -> ScalarBounds:
    scalar: ScalarBounds = {}
    if (warning := scalar_bounds.get("warn")) is not None:
        scalar["warn"] = unit_conversion(warning)
    if (critical := scalar_bounds.get("crit")) is not None:
        scalar["crit"] = unit_conversion(critical)
    if (minimum := scalar_bounds.get("min")) is not None:
        scalar["min"] = unit_conversion(minimum)
    if (maximum := scalar_bounds.get("max")) is not None:
        scalar["max"] = unit_conversion(maximum)
    return scalar


def translate_metrics(perf_data: Perfdata, check_command: str) -> Mapping[str, TranslatedMetric]:
    """Convert Ascii-based performance data as output from a check plug-in
    into floating point numbers, do scaling if necessary.

    Simple example for perf_data: [(u'temp', u'48.1', u'', u'70', u'80', u'', u'')]
    Result for this example:
    { "temp" : {"value" : 48.1, "scalar": {"warn" : 70, "crit" : 80}, "unit" : { ... } }}
    """
    translated_metrics: dict[str, TranslatedMetric] = {}
    color_counter: Counter[Literal["metric", "predictive"]] = Counter()
    for entry in perf_data:
        metric_name, normalized = _normalize_perf_data(entry, check_command)
        mi = _get_extended_metric_info(metric_name, color_counter)
        unit_conversion = mi["unit"].get("conversion", lambda v: v)

        # https://github.com/python/mypy/issues/6462
        # new_entry = normalized
        new_entry = TranslatedMetric(
            orig_name=normalized["orig_name"],
            value=unit_conversion(normalized["value"]),
            scalar=_translated_metric_scalar(unit_conversion, normalized["scalar"]),
            scale=normalized["scale"],
            auto_graph=normalized["auto_graph"],
            title=str(mi["title"]),
            unit=mi["unit"],
            color=mi["color"],
        )

        if metric_name in translated_metrics:
            translated_metrics[metric_name]["orig_name"] = [
                *translated_metrics[metric_name]["orig_name"],
                *new_entry["orig_name"],
            ]
            translated_metrics[metric_name]["scale"] = [
                *translated_metrics[metric_name]["scale"],
                *new_entry["scale"],
            ]
        else:
            translated_metrics[metric_name] = new_entry

    return translated_metrics


def _perf_data_string_from_metric_names(metric_names: list[MetricName]) -> str:
    parts = []
    for var_name in metric_names:
        # Metrics with "," in their name are not allowed. They lead to problems with the RPN processing
        # of the metric system. They are used as separators for the single parts of the expression and
        # since the var_names are used as part of the expressions, they should better not be processed
        # even when reported by the core.
        if "," in var_name:
            continue

        if " " in var_name:
            parts.append('"%s"=1' % var_name)
        else:
            parts.append("%s=1" % var_name)
    return " ".join(parts)


def available_metrics_translated(
    perf_data_string: str,
    rrd_metrics: list[MetricName],
    check_command: str,
) -> Mapping[str, TranslatedMetric]:
    # If we have no RRD files then we cannot paint any graph :-(
    if not rrd_metrics:
        return {}

    perf_data, check_command = parse_perf_data(perf_data_string, check_command)
    rrd_perf_data_string = _perf_data_string_from_metric_names(rrd_metrics)
    rrd_perf_data, check_command = parse_perf_data(rrd_perf_data_string, check_command)
    if not rrd_perf_data + perf_data:
        return {}

    if not perf_data:
        perf_data = rrd_perf_data

    else:
        current_variables = [p.metric_name for p in perf_data]
        for p in rrd_perf_data:
            if p.metric_name not in current_variables:
                perf_data.append(p)

    return translate_metrics(perf_data, check_command)


def translated_metrics_from_row(row: Row) -> Mapping[str, TranslatedMetric]:
    what = "service" if "service_check_command" in row else "host"
    perf_data_string = row[what + "_perf_data"]
    rrd_metrics = row[what + "_metrics"]
    check_command = row[what + "_check_command"]
    return available_metrics_translated(perf_data_string, rrd_metrics, check_command)


# .
#   .--Graphs--------------------------------------------------------------.
#   |                    ____                 _                            |
#   |                   / ___|_ __ __ _ _ __ | |__  ___                    |
#   |                  | |  _| '__/ _` | '_ \| '_ \/ __|                   |
#   |                  | |_| | | | (_| | |_) | | | \__ \                   |
#   |                   \____|_|  \__,_| .__/|_| |_|___/                   |
#   |                                  |_|                                 |
#   +----------------------------------------------------------------------+
#   |  Implementation of time graphs - basic code, not the rendering       |
#   |  Rendering of the graphs is done by PNP4Nagios, we just create PHP   |
#   |  templates for PNP here.                                             |
#   '----------------------------------------------------------------------'


def _graph_templates_internal() -> dict[str, GraphTemplate]:
    # TODO CMK-15246 Checkmk 2.4: Remove legacy objects
    graph_templates: dict[str, GraphTemplate] = {}
    for graph in graphs_from_api.values():
        if isinstance(graph, graphs.Graph):
            graph_templates[graph.name] = GraphTemplate.from_graph(graph)
        elif isinstance(graph, graphs.Bidirectional):
            graph_templates[graph.name] = GraphTemplate.from_bidirectional(graph)
    for template_id, template in graph_info.items():
        if template_id not in graph_templates:
            graph_templates[template_id] = GraphTemplate.from_template(template_id, template)
    return graph_templates


def get_graph_template_choices() -> list[tuple[str, str]]:
    # TODO: v.get("title", k): Use same algorithm as used in
    # GraphIdentificationTemplateBased._parse_template_metric()
    return sorted(
        [(k, v.title or k) for k, v in _graph_templates_internal().items()],
        key=lambda k_v: k_v[1],
    )


def get_graph_template(template_id: str) -> GraphTemplate:
    if template_id.startswith("METRIC_"):
        return GraphTemplate.from_name(template_id)
    if template := _graph_templates_internal().get(template_id):
        return template
    raise MKGeneralException(_("There is no graph template with the id '%s'") % template_id)


def get_graph_templates(
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Iterator[GraphTemplate]:
    if not translated_metrics:
        yield from ()
        return

    explicit_templates = list(
        _get_explicit_graph_templates(
            _graph_templates_internal().values(),
            translated_metrics,
        )
    )
    yield from explicit_templates
    yield from _get_implicit_graph_templates(
        translated_metrics,
        set(
            m.name
            for gt in explicit_templates
            for md in gt.metrics
            for m in md.expression.metrics()
        ),
    )


def _compute_predictive_metrics(
    translated_metrics: Mapping[str, TranslatedMetric],
    metrics_: Sequence[MetricDefinition],
) -> Iterator[MetricDefinition]:
    for metric_defintion in metrics_:
        line_type: Literal["line", "-line"] = (
            "-line" if metric_defintion.line_type.startswith("-") else "line"
        )
        for metric in metric_defintion.expression.metrics():
            if (predict_metric_name := f"predict_{metric.name}") in translated_metrics:
                yield MetricDefinition(
                    expression=Metric(predict_metric_name),
                    line_type=line_type,
                )
            if (predict_lower_metric_name := f"predict_lower_{metric.name}") in translated_metrics:
                yield MetricDefinition(
                    expression=Metric(predict_lower_metric_name),
                    line_type=line_type,
                )


def _get_explicit_graph_templates(
    graph_templates: Iterable[GraphTemplate],
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Iterable[GraphTemplate]:
    for graph_template in graph_templates:
        if metrics_ := applicable_metrics(
            metrics_to_consider=graph_template.metrics,
            conflicting_metrics=graph_template.conflicting_metrics,
            optional_metrics=graph_template.optional_metrics,
            translated_metrics=translated_metrics,
        ):
            yield GraphTemplate(
                id=graph_template.id,
                title=graph_template.title,
                scalars=graph_template.scalars,
                conflicting_metrics=graph_template.conflicting_metrics,
                optional_metrics=graph_template.optional_metrics,
                consolidation_function=graph_template.consolidation_function,
                range=graph_template.range,
                omit_zero_metrics=graph_template.omit_zero_metrics,
                metrics=(
                    list(metrics_) + list(_compute_predictive_metrics(translated_metrics, metrics_))
                ),
            )


def _get_implicit_graph_templates(
    translated_metrics: Mapping[str, TranslatedMetric],
    already_graphed_metrics: Container[str],
) -> Iterable[GraphTemplate]:
    for metric_name, metric_entry in sorted(translated_metrics.items()):
        if metric_entry["auto_graph"] and metric_name not in already_graphed_metrics:
            yield GraphTemplate.from_name(metric_name)


def applicable_metrics(
    *,
    metrics_to_consider: Sequence[MetricDefinition],
    conflicting_metrics: Iterable[str],
    optional_metrics: Sequence[str],
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Sequence[MetricDefinition]:
    # Skip early on conflicting_metrics
    for var in conflicting_metrics:
        if var in translated_metrics:
            return []

    try:
        return list(
            _filter_renderable_graph_metrics(
                metrics_to_consider,
                translated_metrics,
                optional_metrics,
            )
        )
    except KeyError:
        return []


def _filter_renderable_graph_metrics(
    metric_definitions: Sequence[MetricDefinition],
    translated_metrics: Mapping[str, TranslatedMetric],
    optional_metrics: Sequence[str],
) -> Iterator[MetricDefinition]:
    for metric_definition in metric_definitions:
        try:
            metric_definition.expression.evaluate(translated_metrics)
            yield metric_definition
        except KeyError as err:  # because can't find necessary metric_name in translated_metrics
            metric_name = err.args[0]
            if metric_name in optional_metrics:
                continue
            raise err


def get_graph_data_from_livestatus(only_sites, host_name, service_description):
    columns = ["perf_data", "metrics", "check_command"]
    query = livestatus_lql([host_name], columns, service_description)
    what = "host" if service_description == "_HOST_" else "service"
    labels = ["site"] + [f"{what}_{col}" for col in columns]

    with sites.only_sites(only_sites), sites.prepend_site():
        info = dict(zip(labels, sites.live().query_row(query)))

    info["host_name"] = host_name
    if what == "service":
        info["service_description"] = service_description

    return info


def metric_title(metric_name: MetricName) -> str:
    return str(get_extended_metric_info(metric_name)["title"])


# .
#   .--Definitions---------------------------------------------------------.
#   |            ____        __ _       _ _   _                            |
#   |           |  _ \  ___ / _(_)_ __ (_) |_(_) ___  _ __  ___            |
#   |           | | | |/ _ \ |_| | '_ \| | __| |/ _ \| '_ \/ __|           |
#   |           | |_| |  __/  _| | | | | | |_| | (_) | | | \__ \           |
#   |           |____/ \___|_| |_|_| |_|_|\__|_|\___/|_| |_|___/           |
#   |                                                                      |
#   +----------------------------------------------------------------------+

MAX_CORES = 128

MAX_NUMBER_HOPS = 45  # the amount of hop metrics, graphs and perfometers to create

skype_mobile_devices = [
    ("android", "Android", "33/a"),
    ("iphone", "iPhone", "42/a"),
    ("ipad", "iPad", "45/a"),
    ("mac", "Mac", "23/a"),
]
