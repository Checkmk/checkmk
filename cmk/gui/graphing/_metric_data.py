#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
import shlex
import time

# A painter declares the livestatus columns it needs before it knows any row, then reads the values
# back out of a row somebody else fetched. That splits what the engine's own fetch does in one go:
# naming the RRD columns a metric may live in, and merging their values into one series.
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from statistics import fmean
from typing import assert_never

from cmk.ccc.exceptions import MKGeneralException
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine import (
    ConsolidationFunction,
    metric_display_attributes,
    MetricName,
    PerformanceData,
    RRDMetric,
    TimeRange,
    TimeSeries,
)
from cmk.gui.i18n import _, translate_to_current_language
from cmk.gui.log import logger
from cmk.gui.type_defs import ColumnName
from cmk.gui.unit_formatter import NotationFormatter
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.livestatus_client.tables.services import Services

from ._unit import user_specific_unit_from_unit_format
from ._unit_format import unit_to_unit_format


@dataclass(frozen=True, kw_only=True)
class RawPerformanceValue:
    value: float
    warning: float | None = None
    critical: float | None = None
    lower_warning: float | None = None
    lower_critical: float | None = None
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True, kw_only=True)
class RawPerformanceData:
    check_command: str
    values: Mapping[MetricName, RawPerformanceValue]


_VALUE_AND_UNIT = re.compile(r"([0-9.,-]*)(.*)")


def _float_or_int(val: str | None) -> int | float | None:
    if val is None:
        return None
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return None


def _parse_range(val: str | None) -> tuple[float | None, float | None]:
    if not val:
        return None, None
    if ":" not in val:
        return None, _float_or_int(val)
    lower_str, upper_str = val.split(":", 1)
    return (
        _float_or_int(lower_str) if lower_str else None,
        _float_or_int(upper_str) if upper_str else None,
    )


def _split_unit(value_text: str) -> tuple[float | None, str | None]:
    if not value_text or value_text.isspace():
        return None, None
    value_and_unit = re.match(_VALUE_AND_UNIT, value_text)
    assert value_and_unit is not None
    return _float_or_int(value_and_unit[1]) if value_and_unit[1] else None, value_and_unit[2]


def _parse_perf_values(
    data_str: str,
) -> tuple[str, str, tuple[str | None, str | None, str | None, str | None]]:
    varname, values = data_str.split("=", 1)
    varname = varname.replace('"', "").replace("'", "")
    value_parts = values.split(";")
    value = value_parts.pop(0)
    num_fields = len(value_parts)
    return (
        varname,
        value,
        (
            value_parts[0] if num_fields > 0 else None,
            value_parts[1] if num_fields > 1 else None,
            value_parts[2] if num_fields > 2 else None,
            value_parts[3] if num_fields > 3 else None,
        ),
    )


def parse_check_command(check_command: str) -> str:
    parts = check_command.split("!", 1)
    if (
        parts[0] == "check-mk-custom"
        and len(parts) >= 2
        and (parts[1].startswith("check_ping") or "/check_ping" in parts[1])
    ):
        return "check_ping"
    return parts[0]


def _parse_perf_data(
    perf_data_string: str, check_command: str, *, debug: bool
) -> tuple[Mapping[MetricName, RawPerformanceValue], str]:
    check_command = parse_check_command(check_command)

    parts = shlex.split(perf_data_string)
    if parts and parts[-1].startswith("[") and parts[-1].endswith("]"):
        check_command = parts[-1][1:-1]
        del parts[-1]
    check_command = check_command.replace(".", "_")

    raw_perf_data: dict[MetricName, RawPerformanceValue] = {}
    for part in parts:
        try:
            varname, value_text, value_parts = _parse_perf_values(part)
            value, unit_name = _split_unit(value_text)
            if value is None or unit_name is None:
                continue
            lower_warning, warning = _parse_range(value_parts[0])
            lower_critical, critical = _parse_range(value_parts[1])
            raw_perf_data[MetricName(varname)] = RawPerformanceValue(
                value=value,
                warning=warning,
                critical=critical,
                lower_warning=lower_warning,
                lower_critical=lower_critical,
                minimum=_float_or_int(value_parts[2]),
                maximum=_float_or_int(value_parts[3]),
            )
        except Exception as exc:
            logger.exception(
                "Failed to parse perfdata '%(perf_data_string)s'",
                {"perf_data_string": perf_data_string},
            )
            if debug:
                raise exc
    return raw_perf_data, check_command


def parse_performance_data(
    perf_data_string: str,
    check_command: str,
    rrd_metrics: Sequence[str] = (),
    *,
    debug: bool,
) -> RawPerformanceData:
    raw_perf_data, normalized_check_command = _parse_perf_data(
        perf_data_string, check_command, debug=debug
    )
    if rrd_metrics:
        rrd_only, _command = _parse_perf_data(
            " ".join(f'"{m}"=1' if " " in m else f"{m}=1" for m in rrd_metrics if "," not in m),
            check_command,
            debug=debug,
        )
        raw_perf_data = {
            **raw_perf_data,
            **{name: value for name, value in rrd_only.items() if name not in raw_perf_data},
        }
    return RawPerformanceData(check_command=normalized_check_command, values=raw_perf_data)


_PREDICT_PREFIXES = ("predict_lower_", "predict_")

type _TranslationSpec = (
    translations_v1.RenameTo | translations_v1.ScaleBy | translations_v1.RenameToAndScaleBy
)


@dataclass(frozen=True, kw_only=True)
class RRDOriginal:
    metric_name: MetricName
    scale: float


def _normalize_check_command(
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
                else f"check_{check_command.name}"
            )
            return name.replace(".", "_")
        case _:
            assert_never(check_command)


def _specs_for_command(
    check_command: str,
    registered_translations: Sequence[translations_v1.Translation],
) -> Mapping[str, _TranslationSpec]:
    if not check_command:
        return {}

    def _matches(candidate: str) -> Mapping[str, _TranslationSpec]:
        merged: dict[str, _TranslationSpec] = {}
        for translation in registered_translations:
            if candidate in (_normalize_check_command(cmd) for cmd in translation.check_commands):
                merged.update(translation.translations)
        return merged

    if direct := _matches(check_command):
        return direct
    if check_command.startswith("check_mk-mgmt_"):
        return _matches(check_command.replace("check_mk-mgmt_", "check_mk-", 1))
    return {}


def _name_and_scale(old_name: MetricName, spec: _TranslationSpec) -> tuple[MetricName, float]:
    match spec:
        case translations_v1.RenameTo():
            return MetricName(spec.metric_name), 1.0
        case translations_v1.ScaleBy():
            return old_name, spec.factor
        case translations_v1.RenameToAndScaleBy():
            return MetricName(spec.metric_name), spec.factor
        case _:
            assert_never(spec)


def _split_predict_prefix(metric_name: str) -> tuple[str, str]:
    for prefix in _PREDICT_PREFIXES:
        if metric_name.startswith(prefix):
            return prefix, metric_name[len(prefix) :]
    return "", metric_name


def _find_name_and_scale(
    metric_name: MetricName,
    specs: Mapping[str, _TranslationSpec],
) -> tuple[MetricName, float]:
    if (spec := specs.get(metric_name)) is not None:
        return _name_and_scale(metric_name, spec)
    for pattern, spec in specs.items():
        if pattern.startswith("~") and re.compile(pattern[1:]).match(metric_name):
            return _name_and_scale(metric_name, spec)
    return metric_name, 1.0


def _reverse_names(
    canonical_name: MetricName,
    specs: Mapping[str, _TranslationSpec],
) -> Mapping[MetricName, float]:
    result: dict[MetricName, float] = {}
    for old_name, spec in specs.items():
        if old_name.startswith("~"):
            continue
        name, scale = _name_and_scale(MetricName(old_name), spec)
        if name == canonical_name:
            result[MetricName(old_name)] = scale
    return result


def reverse_translated_names(
    canonical_name: MetricName,
    registered_translations: Sequence[translations_v1.Translation],
) -> frozenset[MetricName]:
    # Every raw metric name whose data may belong to this metric, across all check commands: the
    # name itself plus every name any translation renames to it. A regex translation ("~.*rta")
    # maps many names onto one and so cannot be reversed.
    return frozenset(
        {canonical_name}
        | {
            name
            for translation in registered_translations
            for name in _reverse_names(canonical_name, translation.translations)
        }
    )


def _deprecated_originals(
    metric_name: MetricName,
    specs: Mapping[str, _TranslationSpec],
    present: Collection[MetricName],
) -> Iterator[RRDOriginal]:
    prefix, bare_name = _split_predict_prefix(metric_name)
    for old_name, scale in _reverse_names(MetricName(bare_name), specs).items():
        if (column := MetricName(f"{prefix}{old_name}")) not in present:
            yield RRDOriginal(metric_name=column, scale=scale)


@dataclass(frozen=True, kw_only=True)
class _TranslatedColumn:
    original: RRDOriginal
    raw_value: RawPerformanceValue


def _translated_columns(
    specs: Mapping[str, _TranslationSpec],
    raw_values: Mapping[MetricName, RawPerformanceValue],
) -> Mapping[MetricName, Sequence[_TranslatedColumn]]:
    columns: dict[MetricName, list[_TranslatedColumn]] = {}
    for original_name, raw_value in raw_values.items():
        prefix, bare_name = _split_predict_prefix(original_name)
        name, scale = _find_name_and_scale(MetricName(bare_name), specs)
        columns.setdefault(MetricName(f"{prefix}{name}"), []).append(
            _TranslatedColumn(
                original=RRDOriginal(metric_name=original_name, scale=scale),
                raw_value=raw_value,
            )
        )
    return columns


def rrd_originals(
    metric_name: MetricName,
    raw_performance_data: RawPerformanceData,
    registered_translations: Sequence[translations_v1.Translation],
) -> Sequence[RRDOriginal]:
    # The columns a metric's performance data was translated from, each with that translation's
    # factor: a translation that only scales thereby reaches the series just like it reaches the
    # values and the thresholds. A metric without performance data falls back to its own column -
    # no translation applies to a column the perf data never carried, so it is unscaled.
    specs = _specs_for_command(raw_performance_data.check_command, registered_translations)
    columns = _translated_columns(specs, raw_performance_data.values).get(metric_name)
    present = (
        [column.original for column in columns]
        if columns
        else [RRDOriginal(metric_name=metric_name, scale=1.0)]
    )
    return [
        *present,
        *_deprecated_originals(metric_name, specs, {original.metric_name for original in present}),
    ]


def translated_names_and_scales(
    check_command: str,
    raw_metric_names: Sequence[MetricName],
    registered_translations: Sequence[translations_v1.Translation],
) -> Mapping[MetricName, tuple[MetricName, float]]:
    specs = _specs_for_command(check_command, registered_translations)
    mapping: dict[MetricName, tuple[MetricName, float]] = {}
    for raw_metric_name in raw_metric_names:
        prefix, bare_name = _split_predict_prefix(raw_metric_name)
        name, scale = _find_name_and_scale(MetricName(bare_name), specs)
        mapping[raw_metric_name] = (MetricName(f"{prefix}{name}"), scale)
    return mapping


def map_metric_names(
    check_command: str,
    raw_metric_names: Sequence[MetricName],
    registered_translations: Sequence[translations_v1.Translation],
) -> Mapping[MetricName, MetricName]:
    return {
        raw_metric_name: name
        for raw_metric_name, (name, _scale) in translated_names_and_scales(
            check_command, raw_metric_names, registered_translations
        ).items()
    }


def translate_metric_names(
    check_command: str,
    raw_metric_names: Sequence[MetricName],
    registered_translations: Sequence[translations_v1.Translation],
) -> frozenset[MetricName]:
    return frozenset(
        map_metric_names(check_command, raw_metric_names, registered_translations).values()
    )


def _scaled(value: float | None, scale: float) -> float | None:
    return None if value is None else value * scale


def _performance_data(column: _TranslatedColumn) -> PerformanceData:
    raw_value = column.raw_value
    scale = column.original.scale
    return PerformanceData(
        value=_scaled(raw_value.value, scale),
        lower_warning=_scaled(raw_value.lower_warning, scale),
        lower_critical=_scaled(raw_value.lower_critical, scale),
        warning=_scaled(raw_value.warning, scale),
        critical=_scaled(raw_value.critical, scale),
        minimum=_scaled(raw_value.minimum, scale),
        maximum=_scaled(raw_value.maximum, scale),
    )


def translate_performance_data(
    check_command: str,
    raw_values: Mapping[MetricName, RawPerformanceValue],
    registered_translations: Sequence[translations_v1.Translation],
) -> Mapping[MetricName, PerformanceData]:
    specs = _specs_for_command(check_command, registered_translations)
    return {
        name: _performance_data(columns[-1])
        for name, columns in _translated_columns(specs, raw_values).items()
    }


def timestamps(time_range: TimeRange) -> Sequence[int]:
    if time_range.step <= 0:
        return []
    return [t + time_range.step for t in range(time_range.start, time_range.end, time_range.step)]


def _aggregate(
    values: Sequence[float | None], consolidation_function: ConsolidationFunction
) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    match consolidation_function:
        case ConsolidationFunction.MIN:
            return min(present)
        case ConsolidationFunction.MAX:
            return max(present)
        case ConsolidationFunction.AVERAGE:
            return fmean(present)


def _downsample(
    time_series: TimeSeries,
    time_range: TimeRange,
    consolidation_function: ConsolidationFunction,
) -> Sequence[float | None]:
    desired = timestamps(time_range)
    resampled: list[float | None] = []
    bucket: list[float | None] = []
    index = 0
    for timestamp, value in zip(timestamps(time_series.time_range), time_series.values):
        if index < len(desired) and timestamp > desired[index]:
            resampled.append(_aggregate(bucket, consolidation_function))
            bucket = []
            index += 1
        bucket.append(value)
    if (missing := len(desired) - len(resampled)) > 0:
        resampled.append(_aggregate(bucket, consolidation_function))
        resampled += [None] * (missing - 1)
    return resampled


def _forward_fill(time_series: TimeSeries, time_range: TimeRange) -> Sequence[float | None]:
    source = time_series.time_range
    last = len(time_series.values) - 1
    return [
        time_series.values[max(0, min((timestamp - source.start) // source.step, last))]
        for timestamp in range(time_range.start, time_range.end, time_range.step)
    ]


def resample(
    time_series: TimeSeries,
    time_range: TimeRange,
    consolidation_function: ConsolidationFunction,
) -> TimeSeries:
    if time_series.time_range == time_range:
        return time_series
    if not time_series.values or time_series.time_range.step <= 0:
        return TimeSeries(time_range=time_range, values=[None] * len(timestamps(time_range)))
    values = (
        _downsample(time_series, time_range, consolidation_function)
        if time_range.step >= time_series.time_range.step
        else _forward_fill(time_series, time_range)
    )
    return TimeSeries(time_range=time_range, values=values)


def scaled_series(time_series: TimeSeries, scale: float) -> TimeSeries:
    if scale == 1.0:
        return time_series
    return TimeSeries(
        time_range=time_series.time_range,
        values=[None if value is None else value * scale for value in time_series.values],
    )


def merge_series(time_series: Sequence[TimeSeries], time_range: TimeRange) -> TimeSeries:
    return TimeSeries(
        time_range=time_range,
        values=[
            next((value for value in point if value is not None), None)
            for point in zip(*(member.values for member in time_series))
        ],
    )


def chop_last_empty_step(
    time_series: Mapping[RRDMetric, TimeSeries], end: int
) -> Mapping[RRDMetric, TimeSeries]:
    # Drop the empty trailing step of a graph that ends "now": the current RRD step has no data yet,
    # so an all-None last point across every curve is stripped rather than drawn as a gap.
    if not time_series:
        return time_series
    step = next(iter(time_series.values())).time_range.step
    if step <= 0 or abs(time.time() - end) > step:
        return time_series
    if not all(series.values and series.values[-1] is None for series in time_series.values()):
        return time_series
    return {
        metric: TimeSeries(
            time_range=TimeRange(
                start=series.time_range.start, end=series.time_range.end - step, step=step
            ),
            values=series.values[:-1],
        )
        for metric, series in time_series.items()
    }


# The step the columns are requested with. RRD answers with the grid it actually holds, which is
# what the merged series carries; asking for a finer one only changes which archive it picks.
_REQUESTED_STEP = 60


def rrd_column_names(
    metric_name: MetricName,
    consolidation_function: ConsolidationFunction,
    start_time: int,
    end_time: int,
    registered_translations: Sequence[translations_v1.Translation],
) -> Iterator[ColumnName]:
    # Which raw column holds the data cannot be known before a row names its check command, so every
    # name that could translate to this metric is requested and the merge drops what did not.
    time_range = TimeRange(start=start_time, end=end_time, step=_REQUESTED_STEP)
    for name in reverse_translated_names(metric_name, registered_translations):
        yield ColumnName(
            rrd_column_name(
                name, consolidation_function=consolidation_function, time_range=time_range
            )
        )


def _converted(time_series: TimeSeries, conversion: Callable[[float], float]) -> TimeSeries:
    return TimeSeries(
        time_range=time_series.time_range,
        values=[None if value is None else conversion(value) for value in time_series.values],
    )


def _series_of_column(data: Sequence[float | None] | None) -> TimeSeries | None:
    if data is None:
        raise MKGeneralException(_("Cannot retrieve historic data with Nagios core"))
    if len(data) <= 3:
        return None
    if data[0] is None or data[1] is None or data[2] is None:
        raise ValueError(data)
    return TimeSeries(
        time_range=TimeRange(start=int(data[0]), end=int(data[1]), step=int(data[2])),
        values=data[3:],
    )


def merge_rrd_columns(
    target_metric: MetricName,
    rrd_columns: Iterable[tuple[str, Sequence[float | None] | None]],
    check_command: str,
    registered_metrics: Mapping[str, metrics_v1.Metric],
    registered_translations: Sequence[translations_v1.Translation],
    *,
    temperature_unit: TemperatureUnit,
) -> TimeSeries:
    columns = list(rrd_columns)
    # The column name carries the raw metric name it was requested for as its title.
    raw_names = [MetricName(column_name.split(":")[1]) for column_name, _data in columns]
    translated = translated_names_and_scales(check_command, raw_names, registered_translations)

    relevant: list[TimeSeries] = []
    for (_column_name, data), raw_name in zip(columns, raw_names):
        name, scale = translated[raw_name]
        if name != target_metric:
            continue
        if (series := _series_of_column(data)) is not None:
            relevant.append(scaled_series(series, scale))

    if not relevant:
        return TimeSeries(time_range=TimeRange(start=0, end=0, step=0), values=[])

    unit = user_specific_unit_from_unit_format(
        unit_to_unit_format(
            metric_display_attributes(
                target_metric, translate_to_current_language, registered_metrics
            ).unit
        ),
        temperature_unit,
    )
    return _converted(merge_series(relevant, relevant[0].time_range), unit.conversion)


def rrd_column_name(
    metric_name: MetricName,
    *,
    consolidation_function: ConsolidationFunction,
    time_range: TimeRange,
    max_data_points: int | None = None,
) -> str:
    data_range_args: list[int] = [time_range.start, time_range.end, max(1, time_range.step)]
    if max_data_points is not None:
        data_range_args.append(max_data_points)
    # `rrddata` is registered on both the hosts and the services table and the composed column name
    # is the same on either, so building it via Services is fine even for the hosts query that
    # _object_queries emits. `dynamic` validates all parts via LqSafe.
    return Services.rrddata.dynamic(
        metric_name, f"{metric_name}.{consolidation_function}", *data_range_args
    ).name


@dataclass(frozen=True, kw_only=True)
class EvaluatedMetric:
    name: MetricName
    title: str
    color: str
    formatter: NotationFormatter
    performance_data: PerformanceData


def _in_user_unit(
    performance_data: PerformanceData, conversion: Callable[[float], float]
) -> PerformanceData:
    def _converted(value: float | None) -> float | None:
        return None if value is None else conversion(value)

    return PerformanceData(
        value=_converted(performance_data.value),
        lower_warning=_converted(performance_data.lower_warning),
        lower_critical=_converted(performance_data.lower_critical),
        warning=_converted(performance_data.warning),
        critical=_converted(performance_data.critical),
        minimum=_converted(performance_data.minimum),
        maximum=_converted(performance_data.maximum),
    )


def evaluated_metrics(
    perf_data_string: str,
    check_command: str,
    rrd_metrics: Sequence[MetricName] = (),
    *,
    registered_metrics: Mapping[str, metrics_v1.Metric],
    registered_translations: Sequence[translations_v1.Translation],
    temperature_unit: TemperatureUnit,
    debug: bool,
) -> Mapping[MetricName, EvaluatedMetric]:
    raw = parse_performance_data(perf_data_string, check_command, rrd_metrics, debug=debug)
    evaluated = {}
    for name, performance_data in translate_performance_data(
        raw.check_command, raw.values, registered_translations
    ).items():
        attributes = metric_display_attributes(
            name, translate_to_current_language, registered_metrics
        )
        unit = user_specific_unit_from_unit_format(
            unit_to_unit_format(attributes.unit), temperature_unit
        )
        evaluated[name] = EvaluatedMetric(
            name=name,
            title=attributes.title,
            color=attributes.color,
            formatter=unit.formatter,
            performance_data=_in_user_unit(performance_data, unit.conversion),
        )
    return evaluated
