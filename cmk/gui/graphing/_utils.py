#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for main module internals and the plugins"""

import http
import re
import shlex
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal, NewType, NotRequired, TypedDict

from livestatus import livestatus_lql

import cmk.utils.regex
from cmk.utils.metrics import MetricName

from cmk.gui import sites
from cmk.gui.config import active_config, Config
from cmk.gui.exceptions import MKHTTPException
from cmk.gui.log import logger
from cmk.gui.time_series import TimeSeries, TimeSeriesValue
from cmk.gui.type_defs import Perfdata, PerfDataTuple, Row

from ._legacy import check_metrics, CheckMetricEntry
from ._metrics import get_metric_spec_with_color
from ._type_defs import LineType, Original, ScalarBounds, TranslatedMetric


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


_VALUE_AND_UNIT = re.compile(r"([0-9.,-]*)(.*)")


def _split_unit(value_text: str) -> tuple[float | None, str | None]:
    "separate value from unit"
    if not value_text or value_text.isspace():
        return None, None
    value_and_unit = re.match(_VALUE_AND_UNIT, value_text)
    assert value_and_unit is not None  # help mypy a bit, the regex always matches
    return _float_or_int(value_and_unit[1]) if value_and_unit[1] else None, value_and_unit[2]


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
        if parts[1].startswith("check_ping") or parts[1].startswith("./check_ping"):
            return "check_ping"
    return parts[0]


def parse_perf_data(
    perf_data_string: str, check_command: str | None = None, *, config: Config
) -> tuple[Perfdata, str]:
    """Convert perf_data_string into perf_data, extract check_command"""
    # Strip away arguments like in "check_http!-H checkmk.com"
    if check_command is None:
        check_command = ""
    elif hasattr(check_command, "split"):
        check_command = _parse_check_command(check_command)

    # Split the perf data string into parts. Preserve quoted strings!
    parts = shlex.split(perf_data_string)

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
            if config.debug:
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


@dataclass(frozen=True)
class TranslationSpec:
    name: MetricName
    scale: float
    auto_graph: bool
    deprecated: str


def lookup_metric_translations_for_check_command(
    translations: Mapping[str, Mapping[MetricName, CheckMetricEntry]],
    check_command: str | None,  # None due to CMK-13883
) -> Mapping[MetricName, TranslationSpec]:
    if not check_command:
        return {}
    translation_by_metric_names = translations.get(
        check_command,
        (
            translations.get(check_command.replace("check_mk-mgmt_", "check_mk-", 1), {})
            if check_command.startswith("check_mk-mgmt_")
            else {}
        ),
    )
    return {
        m: TranslationSpec(
            name=t.get("name", m),
            scale=t.get("scale", 1.0),
            auto_graph=t.get("auto_graph", True),
            deprecated=t.get("deprecated", ""),
        )
        for m, t in translation_by_metric_names.items()
    }


def find_matching_translation(
    metric_name: MetricName,
    translation_by_metric_names: Mapping[MetricName, TranslationSpec],
) -> TranslationSpec:
    if translation := translation_by_metric_names.get(metric_name):
        return translation
    for orig_metric_name, translation in translation_by_metric_names.items():
        if orig_metric_name.startswith("~") and cmk.utils.regex.regex(orig_metric_name[1:]).match(
            metric_name
        ):  # Regex entry
            return translation
    return TranslationSpec(name=metric_name, scale=1.0, auto_graph=True, deprecated="")


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


def _translated_metric_scalar(
    conversion: Callable[[float], float], scalar_bounds: ScalarBounds
) -> ScalarBounds:
    scalar: ScalarBounds = {}
    if (warning := scalar_bounds.get("warn")) is not None:
        scalar["warn"] = conversion(warning)
    if (critical := scalar_bounds.get("crit")) is not None:
        scalar["crit"] = conversion(critical)
    if (minimum := scalar_bounds.get("min")) is not None:
        scalar["min"] = conversion(minimum)
    if (maximum := scalar_bounds.get("max")) is not None:
        scalar["max"] = conversion(maximum)
    return scalar


def translate_metrics(
    perf_data: Perfdata, check_command: str, explicit_color: str = ""
) -> Mapping[str, TranslatedMetric]:
    """Convert Ascii-based performance data as output from a check plug-in
    into floating point numbers, do scaling if necessary.

    Simple example for perf_data: [(u'temp', u'48.1', u'', u'70', u'80', u'', u'')]
    Result for this example:
    { "temp" : {"value" : 48.1, "scalar": {"warn" : 70, "crit" : 80}, "unit" : { ... } }}
    """
    translated_metrics: dict[str, TranslatedMetric] = {}
    color_counter: Counter[Literal["metric", "predictive"]] = Counter()
    for perf_data_tuple in perf_data:
        translation_spec = find_matching_translation(
            MetricName(perf_data_tuple.lookup_metric_name),
            lookup_metric_translations_for_check_command(check_metrics, check_command),
        )

        if perf_data_tuple.metric_name.startswith("predict_lower_"):
            metric_name = f"predict_lower_{translation_spec.name}"
        elif perf_data_tuple.metric_name.startswith("predict_"):
            metric_name = f"predict_{translation_spec.name}"
        else:
            metric_name = translation_spec.name

        originals = [Original(perf_data_tuple.metric_name, translation_spec.scale)]
        mi = get_metric_spec_with_color(metric_name, color_counter)
        translated_metrics[metric_name] = TranslatedMetric(
            originals=(
                list(translated_metrics[metric_name].originals) + originals
                if metric_name in translated_metrics
                else originals
            ),
            value=mi.unit_info.conversion(perf_data_tuple.value * translation_spec.scale),
            scalar=_translated_metric_scalar(
                mi.unit_info.conversion,
                _scalar_bounds(perf_data_tuple, translation_spec.scale),
            ),
            auto_graph=translation_spec.auto_graph,
            title=str(mi.title),
            unit_info=mi.unit_info,
            color=explicit_color or mi.color,
        )

    return translated_metrics


def available_metrics_translated(
    perf_data_string: str,
    rrd_metrics: list[MetricName],
    check_command: str,
    explicit_color: str = "",
) -> Mapping[str, TranslatedMetric]:
    # If we have no RRD files then we cannot paint any graph :-(
    if not rrd_metrics:
        return {}

    perf_data, check_command = parse_perf_data(
        perf_data_string, check_command, config=active_config
    )
    rrd_perf_data, check_command = parse_perf_data(
        " ".join(
            f'"{m}"=1' if " " in m else f"{m}=1"
            for m in rrd_metrics
            # Metrics with "," in their name are not allowed. They lead to problems with the RPN processing
            # of the metric system. They are used as separators for the single parts of the expression and
            # since the var_names are used as part of the expressions, they should better not be processed
            # even when reported by the core.
            if "," not in m
        ),
        check_command,
        config=active_config,
    )
    current_variables = [p.metric_name for p in perf_data]
    for p in rrd_perf_data:
        if p.metric_name not in current_variables:
            perf_data.append(p)
    return translate_metrics(perf_data, check_command, explicit_color)


def translated_metrics_from_row(
    row: Row, explicit_color: str = ""
) -> Mapping[str, TranslatedMetric]:
    what = "service" if "service_check_command" in row else "host"
    perf_data_string = row[what + "_perf_data"]
    rrd_metrics = row[what + "_metrics"]
    check_command = row[what + "_check_command"]
    return available_metrics_translated(
        perf_data_string, rrd_metrics, check_command, explicit_color
    )


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
