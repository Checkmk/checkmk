#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for main module internals and the plugins"""

import colorsys
import http
import random
import re
import shlex
from collections import OrderedDict
from collections.abc import Callable, Container, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from itertools import chain
from typing import Any, Final, Literal, overload, TypedDict, TypeVar, Union

from pydantic import BaseModel, parse_obj_as

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
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import MKHTTPException, MKUserError
from cmk.gui.graphing._graph_specification import (
    CombinedGraphSpecification,
    ForecastGraphSpecification,
    GraphSpecification,
)
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.type_defs import (
    Choice,
    Choices,
    GraphConsoldiationFunction,
    GraphMetric,
    GraphPresentation,
    HorizontalRule,
    LineType,
    MetricDefinition,
    MetricDefinitionWithoutTitle,
    MetricExpression,
    Perfdata,
    PerfometerSpec,
    RenderableRecipe,
    RGBColor,
    Row,
    TranslatedMetric,
    TranslatedMetrics,
    UnitInfo,
    VisualContext,
)
from cmk.gui.utils.autocompleter_config import ContextAutocompleterConfig
from cmk.gui.utils.html import HTML
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.valuespec import DropdownChoiceWithHostAndServiceHints
from cmk.gui.visuals import livestatus_query_bare

LegacyPerfometer = tuple[str, Any]

ScalarDefinition = Union[str, tuple[str, str | LazyString]]


class MKCombinedGraphLimitExceededError(MKHTTPException):
    status = http.HTTPStatus.BAD_REQUEST


class _CurveMandatory(TypedDict):
    line_type: LineType
    color: str
    title: str
    rrddata: TimeSeries


class Curve(_CurveMandatory, total=False):
    dont_paint: bool
    # Added during runtime by _compute_scalars
    scalars: dict[str, tuple[TimeSeriesValue, str]]


Scalar = tuple[str, str, bool]


class _GraphDataRangeMandatory(TypedDict):
    time_range: TimeRange
    # Forecast graphs represent step as str (see forecasts.py and fetch_rrd_data)
    # colon separated [step length]:[rrd point count]
    step: Seconds | str


class GraphDataRange(_GraphDataRangeMandatory, total=False):
    vertical_range: tuple[float, float]


GraphRangeSpec = tuple[int | str, int | str]
GraphRange = tuple[float | None, float | None]

SizeEx = int


class _GraphTemplateRegistrationMandatory(TypedDict):
    metrics: Sequence[MetricDefinition | tuple[MetricExpression, LineType, LazyString]]


class GraphTemplateRegistration(_GraphTemplateRegistrationMandatory, total=False):
    # All attributes here are optional
    title: str | LazyString
    scalars: Sequence[ScalarDefinition]
    conflicting_metrics: Sequence[str]
    optional_metrics: Sequence[str]
    presentation: GraphPresentation
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
    presentation: GraphPresentation | None
    consolidation_function: GraphConsoldiationFunction | None
    range: GraphRangeSpec | None
    omit_zero_metrics: bool
    metrics: Sequence[MetricDefinition]


@dataclass(frozen=True)
class CombinedSingleMetricSpec:
    datasource: str
    context: VisualContext
    selected_metric: MetricDefinitionWithoutTitle
    consolidation_function: GraphConsoldiationFunction
    presentation: GraphPresentation


class CombinedGraphMetric(GraphMetric, frozen=True):
    metric_definition: MetricDefinition


class GraphRecipeBase(BaseModel, frozen=True):
    title: str
    unit: str
    explicit_vertical_range: GraphRange
    horizontal_rules: Sequence[HorizontalRule]
    omit_zero_metrics: bool
    consolidation_function: GraphConsoldiationFunction | None
    metrics: Sequence[GraphMetric]


class GraphRecipe(GraphRecipeBase, frozen=True):
    specification: GraphSpecification


class CombinedGraphRecipe(GraphRecipe, frozen=True):
    metrics: Sequence[CombinedGraphMetric]
    specification: CombinedGraphSpecification


class ForecastGraphRecipe(GraphRecipe, frozen=True):
    is_forecast: Literal[True]
    model_params: Mapping[str, Any]
    model_params_html: str
    metric_id: tuple[HostName, ServiceName, MetricName_, str] | None
    specification: ForecastGraphSpecification


def parse_raw_graph_recipe(raw: Mapping[str, object]) -> GraphRecipe:
    # See https://github.com/pydantic/pydantic/issues/1847 and the linked mypy issue for the
    # suppressions below
    return parse_obj_as(
        CombinedGraphRecipe | ForecastGraphRecipe | GraphRecipe,  # type: ignore[arg-type]
        raw,
    )


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
    scalar: dict[str, float]
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
        self["%s_%i" % (self._list_identifier, self._item_index)] = item
        self._item_index += 1


class UnitRegistry:
    def __init__(self) -> None:
        self.units: Final[dict[str, UnitInfo | Callable[[], UnitInfo]]] = {}

    def __getitem__(self, unit_id: str) -> UnitInfo:
        item = unit() if callable(unit := self.units[unit_id]) else unit
        item["id"] = unit_id
        item.setdefault("description", item["title"])
        return item

    def __setitem__(self, unit_id: str, unit: UnitInfo | Callable[[], UnitInfo]) -> None:
        self.units[unit_id] = unit

    def keys(self) -> Iterator[str]:
        yield from self.units

    def items(self) -> Iterator[tuple[str, UnitInfo]]:
        yield from ((key, self[key]) for key in self.keys())


# TODO: Refactor to plugin_registry structures
# Note: we cannot simply use dict[str, Callable[[], UnitInfo]] and refactor all unit registrations
# in our codebase because we need to stay compatible with custom extensions
unit_info = UnitRegistry()
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

# Colors:
#
#                   red
#  magenta                       orange
#            11 12 13 14 15 16
#         46                   21
#         45                   22
#   blue  44                   23  yellow
#         43                   24
#         42                   25
#         41                   26
#            36 35 34 33 32 31
#     cyan                       yellow-green
#                  green
#
# Special colors:
# 51  gray
# 52  brown 1
# 53  brown 2
#
# For a new metric_info you have to choose a color. No more hex-codes are needed!
# Instead you can choose a number of the above color ring and a letter 'a' or 'b
# where 'a' represents the basic color and 'b' is a nuance/shading of the basic color.
# Both number and letter must be declared!
#
# Example:
# "color" : "23/a" (basic color yellow)
# "color" : "23/b" (nuance of color yellow)
#
# As an alternative you can call indexed_color with a color index and the maximum
# number of colors you will need to generate a color. This function tries to return
# high contrast colors for "close" indices, so the colors of idx 1 and idx 2 may
# have stronger contrast than the colors at idx 3 and idx 10.

# retrieve an indexed color.
# param idx: the color index
# param total: the total number of colors needed in one graph.
_COLOR_WHEEL_SIZE = 48


def indexed_color(idx: int, total: int) -> str:
    if total < 1:
        raise MKGeneralException(f"{total=} must be larger than zero")
    if not 0 <= idx <= total:
        raise MKGeneralException(f"{idx=} must be in the range 0 <= idx <= {total=}.")

    if idx < _COLOR_WHEEL_SIZE:
        # use colors from the color wheel if possible
        base_col = (idx % 4) + 1
        tone = ((idx // 4) % 6) + 1
        shade = "a" if idx % 8 < 4 else "b"
        return "%d%d/%s" % (base_col, tone, shade)

    # generate distinct rgb values. these may be ugly ; also, they
    # may overlap with the colors from the wheel
    idx_shifted = idx - _COLOR_WHEEL_SIZE
    total_shifted = total - _COLOR_WHEEL_SIZE

    # 7 possible rgb combinations: # red, green, blue, red+green, red+blue, green+blue, red+green+blue
    rgb_combination = idx_shifted % 7
    red = int(rgb_combination in [0, 3, 4, 6])
    green = int(rgb_combination in [1, 3, 5, 6])
    blue = int(rgb_combination in [2, 4, 5, 6])

    # avoid too dark and too light greys
    if red and green and blue:
        rgb_value_min = 100
        rgb_value_max = 200
    # avoid too dark colors (cannot be distinguished)
    else:
        rgb_value_min = 60
        rgb_value_max = 230

    rgb_value = rgb_value_min + int(
        (rgb_value_max - rgb_value_min) * (1 - idx_shifted / total_shifted)
    )

    return rgb_color_to_hex_color(red * rgb_value, green * rgb_value, blue * rgb_value)


def parse_perf_values(
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


def split_unit(value_text: str) -> tuple[float | None, str | None]:
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
            varname, value_text, value_parts = parse_perf_values(part)

            value, unit_name = split_unit(value_text)
            if value is None or unit_name is None:
                continue  # ignore useless empty variable

            perf_data.append(
                (
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


def scalar_bounds(perfvar_bounds, scale) -> dict[str, float]:  # type: ignore[no-untyped-def]
    """rescale "warn, crit, min, max" PERFVAR_BOUNDS values

    Return "None" entries if no performance data and hence no scalars are available
    """

    scalars = {}
    for name, value in zip(("warn", "crit", "min", "max"), perfvar_bounds):
        if value is not None:
            scalars[name] = float(value) * scale
    return scalars


def normalize_perf_data(  # type: ignore[no-untyped-def]
    perf_data, check_command
) -> tuple[str, NormalizedPerfData]:
    translation_entry = perfvar_translation(perf_data[0], check_command)

    new_entry: NormalizedPerfData = {
        "orig_name": [perf_data[0]],
        "value": perf_data[1] * translation_entry["scale"],
        "scalar": scalar_bounds(perf_data[3:], translation_entry["scale"]),
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

        metric_name, normalized = normalize_perf_data(entry, check_command)
        mi, color_index = get_metric_info(metric_name, color_index)
        unit_conversion = mi["unit"].get("conversion", lambda v: v)

        # https://github.com/python/mypy/issues/6462
        # new_entry = normalized
        new_entry: TranslatedMetric = {
            "orig_name": normalized["orig_name"],
            "value": unit_conversion(normalized["value"]),
            "scalar": {k: unit_conversion(v) for k, v in normalized["scalar"].items()},
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


def perf_data_string_from_metric_names(metric_names: list[MetricName_]) -> str:
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

    rrd_perf_data_string = perf_data_string_from_metric_names(rrd_metrics)
    rrd_perf_data, check_command = parse_perf_data(rrd_perf_data_string, check_command)
    if not rrd_perf_data + perf_data:
        return {}

    if not perf_data:
        perf_data = rrd_perf_data

    else:
        current_variables = [x[0] for x in perf_data]
        for entry in rrd_perf_data:
            if entry[0] not in current_variables:
                perf_data.append(entry)

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
# TODO: Refactor evaluate and all helpers into single class


def split_expression(expression: MetricExpression) -> tuple[str, str | None, str | None]:
    explicit_color = None
    if "#" in expression:
        expression, explicit_color = expression.rsplit("#", 1)  # drop appended color information

    explicit_unit_name = None
    if "@" in expression:
        expression, explicit_unit_name = expression.rsplit("@", 1)  # appended unit name

    return expression, explicit_unit_name, explicit_color


@overload
def evaluate(
    expression: MetricExpression,
    translated_metrics: TranslatedMetrics,
) -> tuple[float, UnitInfo, str]:
    ...


@overload
def evaluate(
    expression: int | float,
    translated_metrics: TranslatedMetrics,
) -> tuple[float | None, UnitInfo, str]:
    ...


# Evaluates an expression, returns a triple of value, unit and color.
# e.g. "fs_used:max"    -> 12.455, "b", "#00ffc6",
# e.g. "fs_used(%)"     -> 17.5,   "%", "#00ffc6",
# e.g. "fs_used:max(%)" -> 100.0,  "%", "#00ffc6",
# e.g. 123.4            -> 123.4,  "",  "#000000"
# e.g. "123.4#ff0000"   -> 123.4,  "",  "#ff0000",
# Note:
# "fs_growth.max" is the same as fs_growth. The .max is just
# relevant when fetching RRD data and is used for selecting
# the consolidation function MAX.
def evaluate(
    expression: MetricExpression | int | float,
    translated_metrics: TranslatedMetrics,
) -> tuple[float | None, UnitInfo, str]:
    if isinstance(expression, (float, int)):
        return _evaluate_literal(expression, translated_metrics)

    expression, explicit_unit_name, explicit_color = split_expression(expression)

    value, unit, color = _evaluate_rpn(expression, translated_metrics)

    if explicit_color:
        color = "#" + explicit_color

    if explicit_unit_name:
        unit = unit_info[explicit_unit_name]

    return value, unit, color


def _evaluate_rpn(
    expression: MetricExpression,
    translated_metrics: TranslatedMetrics,
) -> tuple[float, UnitInfo, str]:
    # stack of (value, unit, color)
    return stack_resolver(
        expression.split(","),
        lambda x: x in rpn_operators,
        lambda op, a, b: rpn_operators[op](a, b),
        lambda x: _evaluate_literal(x, translated_metrics),
    )


_TAtom = TypeVar("_TAtom")
_TStackElement = TypeVar("_TStackElement")


def stack_resolver(
    elements: Sequence[_TAtom],
    is_operator: Callable[[_TAtom], bool],
    apply_operator: Callable[[_TAtom, _TStackElement, _TStackElement], _TStackElement],
    apply_element: Callable[[_TAtom], _TStackElement],
) -> _TStackElement:
    stack: list[_TStackElement] = []
    for element in elements:
        if is_operator(element):
            if len(stack) < 2:
                raise MKGeneralException(
                    "Syntax error in expression '%s': too few operands"
                    % ", ".join(map(str, elements))
                )
            op2 = stack.pop()
            op1 = stack.pop()
            stack.append(apply_operator(element, op1, op2))
        else:
            stack.append(apply_element(element))

    if len(stack) != 1:
        raise MKGeneralException(
            "Syntax error in expression '%s': too many operands left"
            % ", ".join(map(str, elements))
        )

    return stack[0]


# TODO: Do real unit computation, detect non-matching units
rpn_operators = {
    "+": lambda a, b: ((a[0] + b[0]), _unit_mult(a[1], b[1]), _choose_operator_color(a[2], b[2])),
    "-": lambda a, b: ((a[0] - b[0]), _unit_sub(a[1], b[1]), _choose_operator_color(a[2], b[2])),
    "*": lambda a, b: ((a[0] * b[0]), _unit_add(a[1], b[1]), _choose_operator_color(a[2], b[2])),
    # Handle zero division by always adding a tiny bit to the divisor
    "/": lambda a, b: (
        (a[0] / (b[0] + 1e-16)),
        _unit_div(a[1], b[1]),
        _choose_operator_color(a[2], b[2]),
    ),
    ">": lambda a, b: ((a[0] > b[0] and 1.0 or 0.0), unit_info[""], "#000000"),
    "<": lambda a, b: ((a[0] < b[0] and 1.0 or 0.0), unit_info[""], "#000000"),
    ">=": lambda a, b: ((a[0] >= b[0] and 1.0 or 0.0), unit_info[""], "#000000"),
    "<=": lambda a, b: ((a[0] <= b[0] and 1.0 or 0.0), unit_info[""], "#000000"),
    "MIN": lambda a, b: _operator_minmax(a, b, min),
    "MAX": lambda a, b: _operator_minmax(a, b, max),
}


# TODO: real unit computation!
def _unit_mult(u1: dict[str, Any], u2: dict[str, Any]) -> dict[str, Any]:
    return u2 if u1 in (unit_info[""], unit_info["count"]) else u1


_unit_div: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] = _unit_mult
_unit_add: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] = _unit_mult
_unit_sub: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] = _unit_mult


def _choose_operator_color(a: str, b: str) -> str:
    if a == "#000000":
        return b
    if b == "#000000":
        return a
    return render_color(_mix_colors(parse_color(a), parse_color(b)))


def _operator_minmax(a, b, func):
    v = func(a[0], b[0])
    # Use unit and color of the winner. If the winner
    # has none (e.g. it is a scalar like 0), then take
    # unit and color of the loser.
    if v == a[0]:
        winner = a
        loser = b
    else:
        winner = b
        loser = a

    if winner[1] != unit_info[""]:
        unit = winner[1]
    else:
        unit = loser[1]

    return v, unit, winner[2] or loser[2]


def _evaluate_literal(
    expression: int | float | str,
    translated_metrics: TranslatedMetrics,
) -> tuple[float | None, UnitInfo, str]:
    if isinstance(expression, int):
        return float(expression), unit_info["count"], "#000000"

    if isinstance(expression, float):
        return expression, unit_info[""], "#000000"

    if val := _float_or_int(expression):
        if expression not in translated_metrics:
            return float(val), unit_info[""], "#000000"

    varname = drop_metric_consolidation_advice(expression)

    percent = varname.endswith("(%)")
    if percent:
        varname = varname[:-3]

    if ":" in varname:
        varname, scalarname = varname.split(":")
        value = translated_metrics[varname]["scalar"].get(scalarname)
        color = scalar_colors.get(scalarname, "#808080")
    else:
        value = translated_metrics[varname]["value"]
        color = translated_metrics[varname]["color"]

    if percent and value is not None:
        maxvalue = translated_metrics[varname]["scalar"]["max"]
        if maxvalue != 0:
            value = 100.0 * float(value) / maxvalue
        else:
            value = 0.0
        unit = unit_info["%"]
    else:
        unit = translated_metrics[varname]["unit"]

    return value, unit, color


@dataclass(frozen=True)
class TimeSeriesMetaData:
    title: str | None = None
    color: str | None = None
    line_type: str = ""


@dataclass(frozen=True)
class AugmentedTimeSeries:
    data: TimeSeries
    metadata: TimeSeriesMetaData = TimeSeriesMetaData()


ExpressionParams = Sequence[Any]
ExpressionFunc = Callable[[ExpressionParams, RRDData], Sequence[AugmentedTimeSeries]]


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
    return {
        template_id: GraphTemplate(
            id=template_id,
            title=str(template["title"]) if "title" in template else None,
            scalars=template.get("scalars", []),
            conflicting_metrics=template.get("conflicting_metrics", []),
            optional_metrics=template.get("optional_metrics", []),
            presentation=template.get("presentation"),
            consolidation_function=template.get("consolidation_function"),
            range=template.get("range"),
            omit_zero_metrics=template.get("omit_zero_metrics", False),
            # mypy cannot infere types based on tuple length, so we would need two typeguards here ...
            # https://github.com/python/mypy/issues/1178
            metrics=[
                (
                    metric
                    if len(metric) == 2
                    else (
                        metric[0],
                        metric[1],
                        str(
                            metric[2],  # type: ignore[misc]
                        ),
                    )
                )
                for metric in template["metrics"]
            ],
        )
        for template_id, template in graph_info.items()
    }


def get_graph_range(
    graph_template: GraphTemplate, translated_metrics: TranslatedMetrics
) -> GraphRange:
    if not graph_template.range:
        return None, None  # Compute range of displayed data points

    try:
        return (
            evaluate(graph_template.range[0], translated_metrics)[0],
            evaluate(graph_template.range[1], translated_metrics)[0],
        )
    except Exception:
        return None, None


def replace_expressions(text: str, translated_metrics: TranslatedMetrics) -> str:
    """Replace expressions in strings like CPU Load - %(load1:max@count) CPU Cores"""

    def eval_to_string(match) -> str:  # type: ignore[no-untyped-def]
        expression = match.group()[2:-1]
        value, unit, _color = evaluate(expression, translated_metrics)
        if value is not None:
            return unit["render"](value)
        return _("n/a")

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
        return generic_graph_template(template_id[7:])
    if template_id in graph_info:
        return graph_templates_internal()[template_id]
    raise MKGeneralException(_("There is no graph template with the id '%s'") % template_id)


def generic_graph_template(metric_name: str) -> GraphTemplate:
    return GraphTemplate(
        id="METRIC_" + metric_name,
        title=None,
        metrics=[
            (metric_name, "area"),
        ],
        scalars=[
            metric_name + ":warn",
            metric_name + ":crit",
        ],
        conflicting_metrics=[],
        optional_metrics=[],
        presentation=None,
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
        _get_graphed_metrics(explicit_templates),
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
                presentation=graph_template.presentation,
                consolidation_function=graph_template.consolidation_function,
                range=graph_template.range,
                omit_zero_metrics=graph_template.omit_zero_metrics,
                metrics=metrics,
            )


def _get_graphed_metrics(graph_templates: Iterable[GraphTemplate]) -> set[str]:
    return set(chain.from_iterable(map(_metrics_used_by_graph, graph_templates)))


def _get_implicit_graph_templates(
    translated_metrics: TranslatedMetrics,
    already_graphed_metrics: Container[str],
) -> Iterable[GraphTemplate]:
    for metric_name, metric_entry in sorted(translated_metrics.items()):
        if metric_entry["auto_graph"] and metric_name not in already_graphed_metrics:
            yield generic_graph_template(metric_name)


def _metrics_used_by_graph(graph_template: GraphTemplate) -> Iterable[str]:
    for metric_definition in graph_template.metrics:
        yield from metrics_used_in_expression(metric_definition[0])


def metrics_used_in_expression(metric_expression: MetricExpression) -> Iterator[str]:
    for part in split_expression(metric_expression)[0].split(","):
        metric_name = drop_metric_consolidation_advice(part)
        if metric_name not in rpn_operators:
            yield metric_name


def drop_metric_consolidation_advice(expression: MetricExpression) -> str:
    if any(expression.endswith(cf) for cf in [".max", ".min", ".average"]):
        return expression.rsplit(".", 1)[0]
    return expression


def applicable_metrics(
    *,
    metrics_to_consider: Sequence[MetricDefinition],
    conflicting_metrics: Iterable[str],
    optional_metrics: Sequence[str],
    translated_metrics: TranslatedMetrics,
) -> list[MetricDefinition] | None:
    # Skip early on conflicting_metrics
    for var in conflicting_metrics:
        if var in translated_metrics:
            return None

    try:
        reduced_metrics = list(
            _filter_renderable_graph_metrics(
                metrics_to_consider,
                translated_metrics,
                optional_metrics,
            )
        )
    except KeyError:
        return None

    return reduced_metrics or None


def _filter_renderable_graph_metrics(
    metric_definitions: Sequence[MetricDefinition],
    translated_metrics: TranslatedMetrics,
    optional_metrics: Sequence[str],
) -> Iterator[MetricDefinition]:
    for metric_definition in metric_definitions:
        try:
            evaluate(metric_definition[0], translated_metrics)
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


def metric_recipe_and_unit(
    host_name: HostName | str,
    service_description: ServiceName,
    metric_name: MetricName_,
    consolidation_function: str,
    line_type: str = "stack",
    visible: bool = True,
) -> tuple[RenderableRecipe, str]:
    mi = metric_info.get(metric_name, {})
    return (
        RenderableRecipe(
            title=metric_title(metric_name),
            expression=("rrd", host_name, service_description, metric_name, consolidation_function),
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
            value, unit, color = evaluate(expression, translated_metrics)
            if value:
                horizontal_rules.append(
                    (
                        value,
                        unit["render"](value),
                        color,
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
# TODO: Refactor color stuff to dedicatedclass

# Try to distribute colors in a whay that the psychological
# colors distance is distributed evenly.
_hsv_color_distribution = [
    (0.1, 10.0),  # orange ... red
    (0.2, 10.0),  # orange ... yellow(-greenish)
    (0.3, 5.0),  # green-yellow
    (0.4, 2.0),  # green
    (0.5, 5.0),  # green .... cyan
    (0.6, 20.0),  # cyan ... seablue
    (0.7, 10.0),  # seablue ... dark blue
    (0.8, 20.0),  # dark blue ... violet
    (0.9, 20.0),  # violet .. magenta
    (1.0, 20.0),  # magenta .. red
]

_cmk_color_palette = {
    # do not use:
    #   "0"     : (0.33, 1, 1),  # green
    #   "1"     : (0.167, 1, 1), # yellow
    #   "2"     : (0, 1, 1),     # red
    # red area
    "11": (0.775, 1, 1),
    "12": (0.8, 1, 1),
    "13": (0.83, 1, 1),
    "14": (0.05, 1, 1),
    "15": (0.08, 1, 1),
    "16": (0.105, 1, 1),
    # yellow area
    "21": (0.13, 1, 1),
    "22": (0.14, 1, 1),
    "23": (0.155, 1, 1),
    "24": (0.185, 1, 1),
    "25": (0.21, 1, 1),
    "26": (0.25, 1, 1),
    # green area
    "31": (0.45, 1, 1),
    "32": (0.5, 1, 1),
    "33": (0.515, 1, 1),
    "34": (0.53, 1, 1),
    "35": (0.55, 1, 1),
    "36": (0.57, 1, 1),
    # blue area
    "41": (0.59, 1, 1),
    "42": (0.62, 1, 1),
    "43": (0.66, 1, 1),
    "44": (0.71, 1, 1),
    "45": (0.73, 1, 1),
    "46": (0.75, 1, 1),
    # special colors
    "51": (0, 0, 0.5),  # grey_50
    "52": (0.067, 0.7, 0.5),  # brown 1
    "53": (0.083, 0.8, 0.55),  # brown 2
}


def rgb_color_to_hex_color(red: int, green: int, blue: int) -> str:
    return f"#{red:02x}{green:02x}{blue:02x}"


def hex_color_to_rgb_color(color: str) -> tuple[int, int, int]:
    """Convert '#112233' or '#123' to (17, 34, 51)"""
    full_color = color
    if len(full_color) == 4:
        # 3-digit hex codes means that both the values (RR, GG, BB) are the same for each component
        # for instance '#ff00cc' can also be written like '#f0c'
        full_color = "#" + full_color[1] * 2 + full_color[2] * 2 + full_color[3] * 2
    try:
        return int(full_color[1:3], 16), int(full_color[3:5], 16), int(full_color[5:7], 16)
    except Exception:
        raise MKGeneralException(_("Invalid color specification '%s'") % color)


# These colors are also used in the CSS stylesheets, do not change one without changing the other.
MONITORING_STATUS_COLORS = {
    "critical/down": rgb_color_to_hex_color(255, 50, 50),
    "unknown/unreachable": rgb_color_to_hex_color(255, 136, 0),
    "warning": rgb_color_to_hex_color(255, 208, 0),
    "in_downtime": rgb_color_to_hex_color(60, 194, 255),
    "on_down_host": rgb_color_to_hex_color(16, 99, 176),
    "ok/up": rgb_color_to_hex_color(19, 211, 137),
}

scalar_colors = {
    "warn": MONITORING_STATUS_COLORS["warning"],
    "crit": MONITORING_STATUS_COLORS["critical/down"],
}


def get_palette_color_by_index(i: int, shading="a") -> str:  # type: ignore[no-untyped-def]
    color_key = sorted(_cmk_color_palette.keys())[i % len(_cmk_color_palette)]
    return f"{color_key}/{shading}"


def get_next_random_palette_color() -> str:
    keys = list(_cmk_color_palette.keys())
    if "random_color_index" in g:
        last_index = g.random_color_index
    else:
        last_index = random.randint(0, len(keys))
    index = (last_index + 1) % len(keys)
    g.random_color_index = index
    return parse_color_into_hexrgb("%s/a" % keys[index])


def get_n_different_colors(n: int) -> list[str]:
    """Return a list of colors that are as different as possible (visually)
    by distributing them on the HSV color wheel."""
    total_weight = sum(x[1] for x in _hsv_color_distribution)

    colors: list[str] = []
    while len(colors) < n:
        weight_index = int(len(colors) * total_weight / n)
        hue = _get_hue_by_weight_index(weight_index)
        colors.append(hsv_to_hexrgb((hue, 1, 1)))
    return colors


def _get_hue_by_weight_index(weight_index: float) -> float:
    section_begin = 0.0
    for section_end, section_weight in _hsv_color_distribution:
        if weight_index < section_weight:
            section_size = section_end - section_begin
            hue = section_begin + int((weight_index / section_weight) * section_size)
            return hue
        weight_index -= section_weight
        section_begin = section_end
    return 0.0  # Hmmm...


# 23/c -> #ff8040
# #ff8040 -> #ff8040
def parse_color_into_hexrgb(color_string: str) -> str:
    if color_string[0] == "#":
        return color_string

    if "/" in color_string:
        cmk_color_index, color_shading = color_string.split("/")
        hsv = _cmk_color_palette[cmk_color_index]

        # Colors of the yellow ("2") and green ("3") area need to be darkened (in third place of the hsv tuple),
        # colors of the red and blue area need to be brightened (in second place of the hsv tuple).
        # For both shadings we need different factors.
        if color_shading == "b":
            factors = (1.0, 1.0, 0.8) if cmk_color_index[0] in ["2", "3"] else (1.0, 0.6, 1.0)
            hsv = _pointwise_multiplication(hsv, factors)

        color_hexrgb = hsv_to_hexrgb(hsv)
        return color_hexrgb

    return "#808080"


def _pointwise_multiplication(
    c1: tuple[float, float, float], c2: tuple[float, float, float]
) -> tuple[float, float, float]:
    components = list(x * y for x, y in zip(c1, c2))
    return components[0], components[1], components[2]


def hsv_to_hexrgb(hsv: tuple[float, float, float]) -> str:
    return render_color(colorsys.hsv_to_rgb(*hsv))


def render_color(color_rgb: RGBColor) -> str:
    return rgb_color_to_hex_color(
        int(color_rgb[0] * 255),
        int(color_rgb[1] * 255),
        int(color_rgb[2] * 255),
    )


def parse_color(color: str) -> RGBColor:
    """Convert '#ff0080' to (1.5, 0.0, 0.5)"""
    rgb = hex_color_to_rgb_color(color)
    return rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0


def fade_color(rgb, v):
    gray = _rgb_to_gray(rgb)
    if gray > 0.5:
        return darken_color(rgb, v)
    return lighten_color(rgb, v)


def darken_color(rgb, v):
    """Make a color darker. v ranges from 0 (not darker) to 1 (black)"""

    def darken(x, v):
        return x * (1.0 - v)

    return tuple(darken(x, v) for x in rgb)


def lighten_color(rgb, v):
    """Make a color lighter. v ranges from 0 (not lighter) to 1 (white)"""

    def lighten(x, v):
        return x + ((1.0 - x) * v)

    return tuple(lighten(x, v) for x in rgb)


def _rgb_to_gray(rgb):
    r, gr, b = rgb
    return 0.21 * r + 0.72 * gr + 0.07 * b


def _mix_colors(a, b):
    return tuple((ca + cb) / 2.0 for (ca, cb) in zip(a, b))


def render_color_icon(color: str) -> HTML:
    return HTMLWriter.render_div(
        "",
        class_="color",
        # NOTE: When we drop support for IE11 we can use #%s4c instead of rgba(...)
        style="background-color: rgba(%d, %d, %d, 0.3); border-color: %s;"
        % (*hex_color_to_rgb_color(color), color),
    )


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
        parsed_perf_data, check_command = parse_perf_data(
            row["service_perf_data"], row["service_check_command"]
        )
        known_metrics = set([perf[0] for perf in parsed_perf_data] + row["service_metrics"])
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
