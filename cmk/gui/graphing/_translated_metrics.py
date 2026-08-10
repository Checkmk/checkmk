#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for main module internals and the plugins"""

import re
import shlex
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, TypedDict

import cmk.ccc.regex
from cmk.gui.log import logger
from cmk.gui.type_defs import Perfdata, PerfDataTuple, Row
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.utils.metrics import MetricName
from cmk.utils.misc import pnp_cleanup

from ._from_api import RegisteredMetric
from ._legacy import check_metrics, CheckMetricEntry
from ._metrics import get_metric_spec_with_color
from ._unit import ConvertibleUnitSpecification, user_specific_unit

_PREDICT_LOWER_PREFIX = "predict_lower_"
_PREDICT_PREFIX = "predict_"


def _normalized_metric_name(metric_name: str) -> MetricName:
    """Bring a metric name into the form the translation tables are keyed by."""
    return MetricName(pnp_cleanup(metric_name.replace('"', "").replace("'", "")))


def _parse_perf_values(
    data_str: str,
) -> tuple[str, str, tuple[str | None, str | None, str | None, str | None]]:
    "convert perf str into a tuple with values"
    varname, values = data_str.split("=", 1)
    varname = _normalized_metric_name(varname)

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


def _split_unit(value_text: str) -> tuple[float | None, str | None]:
    "separate value from unit"
    if not value_text or value_text.isspace():
        return None, None
    value_and_unit = re.match(_VALUE_AND_UNIT, value_text)
    assert value_and_unit is not None  # help mypy a bit, the regex always matches
    return _float_or_int(value_and_unit[1]) if value_and_unit[1] else None, value_and_unit[2]


def _compute_lookup_metric_name(metric_name: str) -> str:
    if metric_name.startswith(_PREDICT_LOWER_PREFIX):
        return metric_name.removeprefix(_PREDICT_LOWER_PREFIX)
    if metric_name.startswith(_PREDICT_PREFIX):
        return metric_name.removeprefix(_PREDICT_PREFIX)
    return metric_name


def _canonical_metric_name(raw_metric_name: MetricName, translated_name: MetricName) -> MetricName:
    """Reattach to the translated name the predictive prefix stripped for lookup."""
    if raw_metric_name.startswith(_PREDICT_LOWER_PREFIX):
        return MetricName(f"{_PREDICT_LOWER_PREFIX}{translated_name}")
    if raw_metric_name.startswith(_PREDICT_PREFIX):
        return MetricName(f"{_PREDICT_PREFIX}{translated_name}")
    return translated_name


def _parse_check_command(check_command: str) -> str:
    # This function handles very special and known cases.
    parts = check_command.split("!", 1)
    if parts[0] == "check-mk-custom" and len(parts) >= 2:
        # re.search(r"(^|/)check_ping(\s|$)", parts[1]) would be better..
        if parts[1].startswith("check_ping") or "/check_ping" in parts[1]:
            return "check_ping"
    return parts[0]


def parse_perf_data(
    perf_data_string: str, check_command: str | None = None, *, debug: bool
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
            if debug:
                raise exc

    return perf_data, check_command


def parse_perf_data_with_rrd_metrics(
    perf_data_string: str,
    check_command: str | None,
    rrd_metrics: Sequence[MetricName],
    *,
    debug: bool,
) -> tuple[Perfdata, str]:
    """Parse the live perf data plus the metrics only the RRDs still know about.

    The RRD-only names run through the same parser as the live ones, so both are normalized
    the same way, and a name the live perf data already carries is not added twice. Only the
    names of the RRD-only entries are meaningful; each carries a placeholder value of 1.
    """
    perf_data, check_command = parse_perf_data(perf_data_string, check_command, debug=debug)
    rrd_perf_data, check_command = parse_perf_data(
        " ".join(
            f'"{m}"=1' if " " in m else f"{m}=1"
            for m in rrd_metrics
            # Metrics with "," in their name are not allowed. They lead to problems with the RPN
            # processing of the metric system. They are used as separators for the single parts of
            # the expression and since the var_names are used as part of the expressions, they
            # should better not be processed even when reported by the core.
            if "," not in m
        ),
        check_command,
        debug=debug,
    )
    live_metric_names = {p.metric_name for p in perf_data}
    rrd_only_perf_data = [p for p in rrd_perf_data if p.metric_name not in live_metric_names]
    return perf_data + rrd_only_perf_data, check_command


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
        if orig_metric_name.startswith("~") and cmk.ccc.regex.regex(orig_metric_name[1:]).match(
            metric_name
        ):  # Regex entry
            return translation
    return TranslationSpec(name=metric_name, scale=1.0, auto_graph=True, deprecated="")


def map_metric_names(
    check_command: str,
    raw_metric_names: Sequence[MetricName],
    translations: Mapping[str, Mapping[MetricName, CheckMetricEntry]],
) -> Mapping[MetricName, MetricName]:
    """Pair every raw perf-data name with the canonical metric name it translates to.

    Names no translation renames map to themselves, so the result has one entry per raw
    name. Several raw names may share one canonical name; the pairing keeps them apart,
    which a set of canonical names cannot.

    Raw names are normalized for the lookup exactly as the perf-data parser normalizes
    them, so a name taken straight from livestatus or an RRD resolves the same way one
    that has already been parsed does. The keys are the names as passed in.
    """
    translation_by_metric_names = lookup_metric_translations_for_check_command(
        translations, check_command
    )
    return {
        raw_metric_name: _canonical_metric_name(
            raw_metric_name,
            find_matching_translation(
                MetricName(_compute_lookup_metric_name(_normalized_metric_name(raw_metric_name))),
                translation_by_metric_names,
            ).name,
        )
        for raw_metric_name in raw_metric_names
    }


@dataclass(frozen=True)
class Original:
    name: str
    scale: float


class ScalarBounds(TypedDict, total=False):
    warn: float
    crit: float
    min: float
    max: float


@dataclass(frozen=True)
class TranslatedMetric:
    originals: Sequence[Original]
    value: float
    scalar: ScalarBounds
    auto_graph: bool
    title: str
    unit_spec: ConvertibleUnitSpecification
    color: str


def _translated_scalar(
    perf_data_tuple: PerfDataTuple,
    scale: float,
    conversion: Callable[[float], float],
) -> ScalarBounds:
    scalars: ScalarBounds = {}
    if perf_data_tuple.warn is not None:
        scalars["warn"] = conversion(float(perf_data_tuple.warn) * scale)
    if perf_data_tuple.crit is not None:
        scalars["crit"] = conversion(float(perf_data_tuple.crit) * scale)
    if perf_data_tuple.min is not None:
        scalars["min"] = conversion(float(perf_data_tuple.min) * scale)
    if perf_data_tuple.max is not None:
        scalars["max"] = conversion(float(perf_data_tuple.max) * scale)
    return scalars


def translate_metrics(
    perf_data: Perfdata,
    check_command: str,
    registered_metrics: Mapping[str, RegisteredMetric],
    explicit_color: str = "",
    *,
    temperature_unit: TemperatureUnit,
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

        metric_name = _canonical_metric_name(
            MetricName(perf_data_tuple.metric_name), translation_spec.name
        )

        originals = [Original(perf_data_tuple.metric_name, translation_spec.scale)]
        mi = get_metric_spec_with_color(metric_name, color_counter, registered_metrics)
        conversion = user_specific_unit(mi.unit_spec, temperature_unit).conversion
        translated_metrics[metric_name] = TranslatedMetric(
            originals=(
                list(translated_metrics[metric_name].originals) + originals
                if metric_name in translated_metrics
                else originals
            ),
            value=conversion(perf_data_tuple.value * translation_spec.scale),
            scalar=_translated_scalar(
                perf_data_tuple,
                translation_spec.scale,
                conversion,
            ),
            auto_graph=translation_spec.auto_graph,
            title=str(mi.title),
            unit_spec=mi.unit_spec,
            color=explicit_color or mi.color,
        )

    return translated_metrics


def available_metrics_translated(
    perf_data_string: str,
    rrd_metrics: list[MetricName],
    check_command: str,
    registered_metrics: Mapping[str, RegisteredMetric],
    explicit_color: str = "",
    *,
    debug: bool,
    temperature_unit: TemperatureUnit,
) -> Mapping[str, TranslatedMetric]:
    # If we have no RRD files then we cannot paint any graph :-(
    if not rrd_metrics:
        return {}

    perf_data, check_command = parse_perf_data_with_rrd_metrics(
        perf_data_string, check_command, rrd_metrics, debug=debug
    )
    return translate_metrics(
        perf_data,
        check_command,
        registered_metrics,
        explicit_color,
        temperature_unit=temperature_unit,
    )


def translated_metrics_from_row(
    row: Row,
    registered_metrics: Mapping[str, RegisteredMetric],
    explicit_color: str = "",
    *,
    debug: bool,
    temperature_unit: TemperatureUnit,
) -> Mapping[str, TranslatedMetric]:
    what = "service" if "service_check_command" in row else "host"
    perf_data_string = row[what + "_perf_data"]
    rrd_metrics = row[what + "_metrics"]
    check_command = row[what + "_check_command"]
    return available_metrics_translated(
        perf_data_string,
        rrd_metrics,
        check_command,
        registered_metrics,
        explicit_color,
        debug=debug,
        temperature_unit=temperature_unit,
    )
