#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for main module internals and the plugins"""

import http
import re
import shlex
from collections import OrderedDict
from collections.abc import Callable, Container, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal, NamedTuple, NewType

from pydantic import BaseModel
from typing_extensions import TypedDict

from livestatus import SiteId

import cmk.utils.regex
import cmk.utils.version as cmk_version
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.metrics import MetricName as MetricName_
from cmk.utils.plugin_registry import Registry
from cmk.utils.prediction import livestatus_lql, Seconds, TimeRange, TimeSeries, TimeSeriesValue
from cmk.utils.servicename import ServiceName
from cmk.utils.version import parse_check_mk_version

import cmk.gui.sites as sites
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKHTTPException, MKUserError
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.type_defs import (
    Choice,
    Choices,
    GraphRenderOptions,
    Perfdata,
    PerfDataTuple,
    PerfometerSpec,
    Row,
    ScalarBounds,
    TranslatedMetric,
    TranslatedMetrics,
    UnitInfo,
    VisualContext,
)
from cmk.gui.utils.autocompleter_config import ContextAutocompleterConfig
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.valuespec import DropdownChoiceWithHostAndServiceHints
from cmk.gui.visuals import livestatus_query_bare

from ._color import (
    get_next_random_palette_color,
    get_palette_color_by_index,
    parse_color_into_hexrgb,
)
from ._expression import parse_expression
from ._graph_specification import (
    GraphMetric,
    GraphSpecification,
    HorizontalRule,
    MetricDefinition,
    MetricOperation,
    MetricOpRRDChoice,
)
from ._type_defs import GraphConsoldiationFunction, GraphPresentation, LineType
from ._unit_info import unit_info

LegacyPerfometer = tuple[str, Any]

ScalarDefinition = str | tuple[str, str | LazyString]


class MKCombinedGraphLimitExceededError(MKHTTPException):
    status = http.HTTPStatus.BAD_REQUEST


class _CurveMandatory(TypedDict):
    line_type: LineType | Literal["ref"]
    color: str
    title: str
    rrddata: TimeSeries


class Curve(_CurveMandatory, total=False):
    # Added during runtime by _compute_scalars
    scalars: dict[str, tuple[TimeSeriesValue, str]]


class _GraphDataRangeMandatory(TypedDict):
    time_range: TimeRange
    # Forecast graphs represent step as str (see forecasts.py and fetch_rrd_data)
    # colon separated [step length]:[rrd point count]
    step: Seconds | str


class GraphDataRange(_GraphDataRangeMandatory, total=False):
    vertical_range: tuple[float, float]


GraphRangeSpec = tuple[int | str, int | str]
GraphRange = tuple[float | None, float | None]
SizeEx = NewType("SizeEx", int)


class _GraphTemplateRegistrationMandatory(TypedDict):
    metrics: Sequence[
        tuple[str, LineType] | tuple[str, LineType, str] | tuple[str, LineType, LazyString]
    ]


class GraphTemplateRegistration(_GraphTemplateRegistrationMandatory, total=False):
    # All attributes here are optional
    title: str | LazyString
    scalars: Sequence[ScalarDefinition]
    conflicting_metrics: Sequence[str]
    optional_metrics: Sequence[str]
    consolidation_function: GraphConsoldiationFunction
    range: GraphRangeSpec
    omit_zero_metrics: bool


@dataclass(frozen=True)
class GraphTemplate:
    id: str
    title: str | None
    scalars: Sequence[ScalarDefinition]
    conflicting_metrics: Sequence[str]
    optional_metrics: Sequence[str]
    consolidation_function: GraphConsoldiationFunction | None
    range: GraphRangeSpec | None
    omit_zero_metrics: bool
    metrics: Sequence[MetricDefinition]


@dataclass(frozen=True)
class CombinedSingleMetricSpec:
    datasource: str
    context: VisualContext
    selected_metric: MetricDefinition
    consolidation_function: GraphConsoldiationFunction
    presentation: GraphPresentation


class AdditionalGraphHTML(BaseModel, frozen=True):
    title: str
    html: str


class GraphRecipeBase(BaseModel, frozen=True):
    title: str
    unit: str
    explicit_vertical_range: GraphRange
    horizontal_rules: Sequence[HorizontalRule]
    omit_zero_metrics: bool
    consolidation_function: GraphConsoldiationFunction | None
    metrics: Sequence[GraphMetric]
    additional_html: AdditionalGraphHTML | None = None
    render_options: GraphRenderOptions = {}
    data_range: GraphDataRange | None = None
    mark_requested_end_time: bool = False


class GraphRecipe(GraphRecipeBase, frozen=True):
    specification: GraphSpecification


RRDDataKey = tuple[SiteId, HostName, ServiceName, str, GraphConsoldiationFunction | None, float]
RRDData = dict[RRDDataKey, TimeSeries]


class MetricUnitColor(TypedDict):
    unit: str
    color: str


class CheckMetricEntry(TypedDict, total=False):
    scale: float
    name: MetricName_
    auto_graph: bool
    deprecated: str


class MetricInfo(TypedDict, total=False):
    # title, unit and color should be required, but metric_info.get(xxx, {}) is
    # used and is not compatible with requied keys
    title: str | LazyString
    unit: str
    color: str
    help: str | LazyString
    render: Callable[[float | int], str]


class MetricInfoExtended(TypedDict, total=False):
    # this is identical to MetricInfo except unit, but one can not override the
    # type of a field so we have to copy everything from MetricInfo
    title: str | LazyString
    unit: UnitInfo
    color: str
    help: str | LazyString
    render: Callable[[float | int], str]


class NormalizedPerfData(TypedDict):
    orig_name: list[str]
    value: float
    scalar: ScalarBounds
    scale: list[float]
    auto_graph: bool


class TranslationInfo(TypedDict):
    name: str
    scale: float
    auto_graph: bool


class AutomaticDict(OrderedDict[str, GraphTemplateRegistration]):
    """Dictionary class with the ability of appending items like provided
    by a list."""

    def __init__(self, list_identifier: str | None = None, start_index: int | None = None) -> None:
        super().__init__(self)
        self._list_identifier = list_identifier or "item"
        self._item_index = start_index or 0

    def append(self, item: GraphTemplateRegistration) -> None:
        # Avoid duplicate graph definitions in case the metric plugins are loaded multiple times.
        # Otherwise, we get duplicate graphs in the UI.
        if self._item_already_appended(item):
            return
        self["%s_%i" % (self._list_identifier, self._item_index)] = item
        self._item_index += 1

    def _item_already_appended(self, item: GraphTemplateRegistration) -> bool:
        return item in [
            graph_template
            for graph_template_id, graph_template in self.items()
            if graph_template_id.startswith(self._list_identifier)
        ]


metric_info: dict[MetricName_, MetricInfo] = {}
check_metrics: dict[str, dict[MetricName_, CheckMetricEntry]] = {}
perfometer_info: list[LegacyPerfometer | PerfometerSpec] = []
# _AutomaticDict is used here to provide some list methods.
# This is needed to maintain backwards-compatibility.
graph_info = AutomaticDict("manual_graph_template")

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


def parse_perf_data(
    perf_data_string: str, check_command: str | None = None
) -> tuple[Perfdata, str]:
    """Convert perf_data_string into perf_data, extract check_command"""
    # Strip away arguments like in "check_http!-H checkmk.com"
    if check_command is None:
        check_command = ""
    elif hasattr(check_command, "split"):
        check_command = check_command.split("!")[0]

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
        MetricName_(perfvar_name),
        lookup_metric_translations_for_check_command(check_metrics, check_command) or {},
    )
    return {
        "name": translation_entry.get("name", perfvar_name),
        "scale": translation_entry.get("scale", 1.0),
        "auto_graph": translation_entry.get("auto_graph", True),
    }


def lookup_metric_translations_for_check_command(
    all_translations: Mapping[str, Mapping[MetricName_, CheckMetricEntry]],
    check_command: str | None,  # None due to CMK-13883
) -> Mapping[MetricName_, CheckMetricEntry] | None:
    if not check_command:
        return None
    return all_translations.get(
        check_command,
        all_translations.get(
            check_command.replace(
                "check_mk-mgmt_",
                "check_mk-",
                1,
            )
        )
        if check_command.startswith("check_mk-mgmt_")
        else None,
    )


def find_matching_translation(
    metric_name: MetricName_,
    translations: Mapping[MetricName_, CheckMetricEntry],
) -> CheckMetricEntry:
    if translation := translations.get(metric_name):
        return translation
    for orig_metric_name, translation in translations.items():
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
) -> tuple[str, NormalizedPerfData]:
    translation_entry = perfvar_translation(perf_data_tuple.metric_name, check_command)

    new_entry: NormalizedPerfData = {
        "orig_name": [perf_data_tuple.metric_name],
        "value": perf_data_tuple.value * translation_entry["scale"],
        "scalar": _scalar_bounds(perf_data_tuple, translation_entry["scale"]),
        "scale": [translation_entry["scale"]],  # needed for graph recipes
        # Do not create graphs for ungraphed metrics if listed here
        "auto_graph": translation_entry["auto_graph"],
    }

    return translation_entry["name"], new_entry


def get_metric_info(metric_name: str, color_index: int) -> tuple[MetricInfoExtended, int]:
    if metric_name in metric_info:
        mi = metric_info[metric_name]
    else:
        color_index += 1
        mi = MetricInfo(
            title=metric_name.title(),
            unit="",
            color=get_palette_color_by_index(color_index),
        )

    mie = MetricInfoExtended(
        title=mi["title"],
        unit=unit_info[mi["unit"]],
        color=parse_color_into_hexrgb(mi["color"]),
    )
    if "help" in mi:
        mie["help"] = mi["help"]
    if "render" in mi:
        mie["render"] = mi["render"]

    return mie, color_index


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


def translate_metrics(perf_data: Perfdata, check_command: str) -> TranslatedMetrics:
    """Convert Ascii-based performance data as output from a check plugin
    into floating point numbers, do scaling if necessary.

    Simple example for perf_data: [(u'temp', u'48.1', u'', u'70', u'80', u'', u'')]
    Result for this example:
    { "temp" : {"value" : 48.1, "scalar": {"warn" : 70, "crit" : 80}, "unit" : { ... } }}
    """
    translated_metrics: TranslatedMetrics = {}
    color_index = 0
    for entry in perf_data:
        metric_name: str

        metric_name, normalized = _normalize_perf_data(entry, check_command)
        mi, color_index = get_metric_info(metric_name, color_index)
        unit_conversion = mi["unit"].get("conversion", lambda v: v)

        # https://github.com/python/mypy/issues/6462
        # new_entry = normalized
        new_entry: TranslatedMetric = {
            "orig_name": normalized["orig_name"],
            "value": unit_conversion(normalized["value"]),
            "scalar": _translated_metric_scalar(unit_conversion, normalized["scalar"]),
            "scale": normalized["scale"],
            "auto_graph": normalized["auto_graph"],
            "title": str(mi["title"]),
            "unit": mi["unit"],
            "color": mi["color"],
        }

        if metric_name in translated_metrics:
            translated_metrics[metric_name]["orig_name"].extend(new_entry["orig_name"])
            translated_metrics[metric_name]["scale"].extend(new_entry["scale"])
        else:
            translated_metrics[metric_name] = new_entry
    return translated_metrics


def _perf_data_string_from_metric_names(metric_names: list[MetricName_]) -> str:
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
    rrd_metrics: list[MetricName_],
    check_command: str,
) -> TranslatedMetrics:
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


def translated_metrics_from_row(row: Row) -> TranslatedMetrics:
    what = "service" if "service_check_command" in row else "host"
    perf_data_string = row[what + "_perf_data"]
    rrd_metrics = row[what + "_metrics"]
    check_command = row[what + "_check_command"]
    return available_metrics_translated(perf_data_string, rrd_metrics, check_command)


# .
#   .--Evaluation----------------------------------------------------------.
#   |          _____            _             _   _                        |
#   |         | ____|_   ____ _| |_   _  __ _| |_(_) ___  _ __             |
#   |         |  _| \ \ / / _` | | | | |/ _` | __| |/ _ \| '_ \            |
#   |         | |___ \ V / (_| | | |_| | (_| | |_| | (_) | | | |           |
#   |         |_____| \_/ \__,_|_|\__,_|\__,_|\__|_|\___/|_| |_|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Parsing of performance data into metrics, evaluation of expressions |
#   '----------------------------------------------------------------------'


@dataclass(frozen=True)
class TimeSeriesMetaData:
    title: str | None = None
    color: str | None = None
    line_type: LineType | Literal["ref"] | None = None


@dataclass(frozen=True)
class AugmentedTimeSeries:
    data: TimeSeries
    metadata: TimeSeriesMetaData = TimeSeriesMetaData()


ExpressionFunc = Callable[[MetricOperation, RRDData], Sequence[AugmentedTimeSeries]]


class TimeSeriesExpressionRegistry(Registry[ExpressionFunc]):
    def plugin_name(self, instance: ExpressionFunc) -> str:
        # mypy does not know this attribute
        return instance._ident  # type: ignore[attr-defined]

    def register_expression(self, ident: str) -> Callable[[ExpressionFunc], ExpressionFunc]:
        def wrap(plugin_func: ExpressionFunc) -> ExpressionFunc:
            if not callable(plugin_func):
                raise TypeError()

            # We define the attribute here. for the `plugin_name` method.
            plugin_func._ident = ident  # type: ignore[attr-defined]

            self.register(plugin_func)
            return plugin_func

        return wrap


time_series_expression_registry = TimeSeriesExpressionRegistry()

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


def graph_templates_internal() -> dict[str, GraphTemplate]:
    def _parse_raw_metric(
        raw_metric: (
            tuple[str, LineType] | tuple[str, LineType, str] | tuple[str, LineType, LazyString]
        )
    ) -> MetricDefinition:
        expression = raw_metric[0]
        line_type = raw_metric[1]
        if len(raw_metric) == 2:
            return MetricDefinition(
                expression=expression,
                line_type=line_type,
            )
        return MetricDefinition(
            expression=expression,
            line_type=line_type,
            title=str(raw_metric[-1]),
        )

    return {
        template_id: GraphTemplate(
            id=template_id,
            title=str(template["title"]) if "title" in template else None,
            scalars=template.get("scalars", []),
            conflicting_metrics=template.get("conflicting_metrics", []),
            optional_metrics=template.get("optional_metrics", []),
            consolidation_function=template.get("consolidation_function"),
            range=template.get("range"),
            omit_zero_metrics=template.get("omit_zero_metrics", False),
            # mypy cannot infere types based on tuple length, so we would need two typeguards here ...
            # https://github.com/python/mypy/issues/1178
            metrics=[_parse_raw_metric(raw_metric) for raw_metric in template["metrics"]],
        )
        for template_id, template in graph_info.items()
    }


def get_graph_range(
    graph_template: GraphTemplate, translated_metrics: TranslatedMetrics
) -> GraphRange:
    if not graph_template.range:
        return None, None  # Compute range of displayed data points

    # TODO really? see test_create_graph_recipe_from_template
    try:
        from_ = (
            parse_expression(graph_template.range[0], translated_metrics)
            .evaluate(translated_metrics)
            .value
        )
    except Exception:
        from_ = None

    try:
        to = (
            parse_expression(graph_template.range[1], translated_metrics)
            .evaluate(translated_metrics)
            .value
        )
    except Exception:
        to = None
    return from_, to


def replace_expressions(text: str, translated_metrics: TranslatedMetrics) -> str:
    """Replace expressions in strings like CPU Load - %(load1:max@count) CPU Cores"""

    def eval_to_string(match) -> str:  # type: ignore[no-untyped-def]
        try:
            result = parse_expression(match.group()[2:-1], translated_metrics).evaluate(
                translated_metrics
            )
        except ValueError:
            return _("n/a")
        return result.unit_info["render"](result.value)

    r = cmk.utils.regex.regex(r"%\([^)]*\)")
    return r.sub(eval_to_string, text)


def get_graph_template_choices() -> list[tuple[str, str]]:
    # TODO: v.get("title", k): Use same algorithm as used in
    # GraphIdentificationTemplateBased._parse_template_metric()
    return sorted(
        [(k, v.title or k) for k, v in graph_templates_internal().items()],
        key=lambda k_v: k_v[1],
    )


def get_graph_template(template_id: str) -> GraphTemplate:
    if template_id.startswith("METRIC_"):
        return _generic_graph_template(template_id[7:])
    if template_id in graph_info:
        return graph_templates_internal()[template_id]
    raise MKGeneralException(_("There is no graph template with the id '%s'") % template_id)


def _generic_graph_template(metric_name: str) -> GraphTemplate:
    return GraphTemplate(
        id="METRIC_" + metric_name,
        title=None,
        metrics=[MetricDefinition(expression=metric_name, line_type="area")],
        scalars=[
            metric_name + ":warn",
            metric_name + ":crit",
        ],
        conflicting_metrics=[],
        optional_metrics=[],
        consolidation_function=None,
        range=None,
        omit_zero_metrics=False,
    )


def get_graph_templates(translated_metrics: TranslatedMetrics) -> Iterator[GraphTemplate]:
    if not translated_metrics:
        yield from ()
        return

    explicit_templates = list(_get_explicit_graph_templates(translated_metrics))
    yield from explicit_templates
    yield from _get_implicit_graph_templates(
        translated_metrics,
        set(
            m.name
            for gt in explicit_templates
            for md in gt.metrics
            for m in parse_expression(md.expression, translated_metrics).metrics()
        ),
    )


def _get_explicit_graph_templates(translated_metrics: TranslatedMetrics) -> Iterable[GraphTemplate]:
    for graph_template in graph_templates_internal().values():
        if metrics := applicable_metrics(
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
                metrics=metrics,
            )


def _get_implicit_graph_templates(
    translated_metrics: TranslatedMetrics,
    already_graphed_metrics: Container[str],
) -> Iterable[GraphTemplate]:
    for metric_name, metric_entry in sorted(translated_metrics.items()):
        if metric_entry["auto_graph"] and metric_name not in already_graphed_metrics:
            yield _generic_graph_template(metric_name)


def applicable_metrics(
    *,
    metrics_to_consider: Sequence[MetricDefinition],
    conflicting_metrics: Iterable[str],
    optional_metrics: Sequence[str],
    translated_metrics: TranslatedMetrics,
) -> list[MetricDefinition]:
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
    translated_metrics: TranslatedMetrics,
    optional_metrics: Sequence[str],
) -> Iterator[MetricDefinition]:
    for metric_definition in metric_definitions:
        try:
            parse_expression(metric_definition.expression, translated_metrics).evaluate(
                translated_metrics
            )
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


def metric_title(metric_name: MetricName_) -> str:
    return str(metric_info.get(metric_name, {}).get("title", metric_name.title()))


class RenderableRecipe(NamedTuple):
    title: str
    expression: MetricOperation
    color: str
    line_type: LineType
    visible: bool


def metric_recipe_and_unit(
    host_name: HostName | str,
    service_description: ServiceName,
    metric_name: MetricName_,
    consolidation_function: str,
    line_type: LineType = "stack",
    visible: bool = True,
) -> tuple[RenderableRecipe, str]:
    def _parse_consolidation_func_name(name: str) -> GraphConsoldiationFunction:
        if name == "max":
            return "max"
        if name == "min":
            return "min"
        if name == "average":
            return "average"
        raise ValueError(name)

    mi = metric_info.get(metric_name, {})
    return (
        RenderableRecipe(
            title=metric_title(metric_name),
            expression=MetricOpRRDChoice(
                host_name=HostName(host_name),
                service_name=service_description,
                metric_name=metric_name,
                consolidation_func_name=_parse_consolidation_func_name(consolidation_function),
            ),
            color=parse_color_into_hexrgb(mi.get("color", get_next_random_palette_color())),
            line_type=line_type,
            visible=visible,
        ),
        mi.get("unit", ""),
    )


def horizontal_rules_from_thresholds(
    thresholds: Iterable[ScalarDefinition],
    translated_metrics: TranslatedMetrics,
) -> list[HorizontalRule]:
    horizontal_rules = []
    for entry in thresholds:
        if isinstance(entry, tuple):
            expression, title = entry
        else:
            expression = entry
            if expression.endswith(":warn"):
                title = _("Warning")
            elif expression.endswith(":crit"):
                title = _("Critical")
            else:
                title = expression

        try:
            if (
                result := parse_expression(expression, translated_metrics).evaluate(
                    translated_metrics
                )
            ).value:
                horizontal_rules.append(
                    (
                        result.value,
                        result.unit_info["render"](result.value),
                        result.color,
                        str(title),
                    )
                )
        # Scalar value like min and max are always optional. This makes configuration
        # of graphs easier.
        except Exception:
            pass

    return horizontal_rules


# .
#   .--Colors--------------------------------------------------------------.
#   |                      ____      _                                     |
#   |                     / ___|___ | | ___  _ __ ___                      |
#   |                    | |   / _ \| |/ _ \| '__/ __|                     |
#   |                    | |__| (_) | | (_) | |  \__ \                     |
#   |                     \____\___/|_|\___/|_|  |___/                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Functions and constants dealing with colors                         |
#   '----------------------------------------------------------------------'


def reverse_translate_into_all_potentially_relevant_metrics(
    canonical_name: MetricName_,
    current_version: int,
    all_translations: Iterable[Mapping[MetricName_, CheckMetricEntry]],
) -> set[MetricName_]:
    return {
        canonical_name,
        *(
            metric_name
            for trans in all_translations
            for metric_name, options in trans.items()
            if canonical_name == options.get("name")
            and (
                # From version check used unified metric, and thus deprecates old translation
                # added a complete stable release, that gives the customer about a year of data
                # under the appropriate metric name.
                # We should however get all metrics unified before Cmk 2.1
                parse_check_mk_version(deprecated) + 10000000
                if (deprecated := options.get("deprecated"))
                else current_version
            )
            >= current_version
            # Note: Reverse translations only work for 1-to-1-mappings, entries such as
            # "~.*rta": {"name": "rta", "scale": m},
            # cannot be reverse-translated, since multiple metric names are apparently mapped to a
            # single new name. This is a design flaw we currently have to live with.
            and not metric_name.startswith("~")
        ),
    }


@lru_cache
def reverse_translate_into_all_potentially_relevant_metrics_cached(
    canonical_name: MetricName_,
) -> set[MetricName_]:
    return reverse_translate_into_all_potentially_relevant_metrics(
        canonical_name,
        parse_check_mk_version(cmk_version.__version__),
        check_metrics.values(),
    )


def metric_choices(check_command: str, perfvars: tuple[MetricName_, ...]) -> Iterator[Choice]:
    for perfvar in perfvars:
        translated = perfvar_translation(perfvar, check_command)
        name = translated["name"]
        mi = metric_info.get(name, {})
        yield name, str(mi.get("title", name.title()))


def metrics_of_query(
    context: VisualContext,
) -> Iterator[Choice]:
    # Fetch host data with the *same* query. This saves one round trip. And head
    # host has at least one service
    columns = [
        "service_description",
        "service_check_command",
        "service_perf_data",
        "service_metrics",
        "host_check_command",
        "host_metrics",
    ]

    row = {}
    for row in livestatus_query_bare("service", context, columns):
        perf_data, check_command = parse_perf_data(
            row["service_perf_data"], row["service_check_command"]
        )
        known_metrics = set([p.metric_name for p in perf_data] + row["service_metrics"])
        yield from metric_choices(str(check_command), tuple(map(str, known_metrics)))

    if row.get("host_check_command"):
        yield from metric_choices(
            str(row["host_check_command"]), tuple(map(str, row["host_metrics"]))
        )


def registered_metrics() -> Iterator[Choice]:
    for metric_id, metric_detail in metric_info.items():
        yield metric_id, str(metric_detail["title"])


class MetricName(DropdownChoiceWithHostAndServiceHints):
    """Factory of a Dropdown menu from all known metric names"""

    ident = "monitored_metrics"

    def __init__(self, **kwargs: Any) -> None:
        # Customer's metrics from local checks or other custom plugins will now appear as metric
        # options extending the registered metric names on the system. Thus assuming the user
        # only selects from available options we skip the input validation(invalid_choice=None)
        # Since it is not possible anymore on the backend to collect the host & service hints
        kwargs_with_defaults: Mapping[str, Any] = {
            "css_spec": ["ajax-vals"],
            "hint_label": _("metric"),
            "title": _("Metric"),
            "regex": re.compile("^[a-zA-Z][a-zA-Z0-9_]*$"),
            "regex_error": _(
                "Metric names must only consist of letters, digits and "
                "underscores and they must start with a letter."
            ),
            "autocompleter": ContextAutocompleterConfig(
                ident=self.ident,
                show_independent_of_context=True,
                dynamic_params_callback_name="host_and_service_hinted_autocompleter",
            ),
            **kwargs,
        }
        super().__init__(**kwargs_with_defaults)

    def _validate_value(self, value: str | None, varprefix: str) -> None:
        if value == "":
            raise MKUserError(varprefix, self._regex_error)
        # dropdown allows empty values by default
        super()._validate_value(value, varprefix)

    def _choices_from_value(self, value: str | None) -> Choices:
        if value is None:
            return list(self.choices())
        # Need to create an on the fly metric option
        return [
            next(
                (
                    (metric_id, str(metric_detail["title"]))
                    for metric_id, metric_detail in metric_info.items()
                    if metric_id == value
                ),
                (value, value.title()),
            )
        ]


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
