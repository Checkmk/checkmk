#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# A painter declares the livestatus columns it needs before it knows any row, then reads the values
# back out of a row somebody else fetched. That splits what the engine's own fetch does in one go:
# naming the RRD columns a metric may live in, and merging their values into one series.

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence

from cmk.ccc.exceptions import MKGeneralException
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine import (
    ConsolidationFunction,
    metric_display_attributes,
    MetricName,
    TimeRange,
    TimeSeries,
)
from cmk.gui.i18n import _, translate_to_current_language
from cmk.gui.type_defs import ColumnName
from cmk.gui.utils.temperate_unit import TemperatureUnit

from ._engine_series import merge_series, scaled_series
from ._engine_translations import reverse_translated_names, translated_names_and_scales
from ._source import rrd_column_name
from ._unit import user_specific_unit_from_unit_format
from ._unit_format import unit_to_unit_format

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
