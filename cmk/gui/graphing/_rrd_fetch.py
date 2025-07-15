#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Core for getting the actual raw data points via Livestatus from RRD"""

import collections
import contextlib
import time
from collections.abc import Callable, Iterable, Iterator, Mapping
from functools import lru_cache

import livestatus
from livestatus import livestatus_lql

import cmk.ccc.version as cmk_version
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.version import parse_check_mk_version

from cmk.utils.metrics import MetricName
from cmk.utils.servicename import ServiceName

from cmk.gui import sites
from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import ColumnName

from ._from_api import RegisteredMetric
from ._graph_specification import GraphDataRange, GraphRecipe
from ._legacy import (
    check_metrics,
    CheckMetricEntry,
)
from ._metric_operation import (
    GraphConsolidationFunction,
    op_func_wrapper,
    RRDData,
    RRDDataKey,
    time_series_operators,
)
from ._metrics import get_metric_spec
from ._time_series import TimeSeries, TimeSeriesValues
from ._translated_metrics import find_matching_translation, TranslationSpec
from ._unit import user_specific_unit


def fetch_rrd_data_for_graph(
    graph_recipe: GraphRecipe,
    graph_data_range: GraphDataRange,
    registered_metrics: Mapping[str, RegisteredMetric],
) -> RRDData:
    conversion = user_specific_unit(graph_recipe.unit_spec, user, active_config).conversion
    by_service = _group_needed_rrd_data_by_service(
        key
        for metric in graph_recipe.metrics
        for key in metric.operation.keys(registered_metrics)
        if isinstance(key, RRDDataKey)
    )
    rrd_data: dict[RRDDataKey, TimeSeries] = {}
    for (site, host_name, service_description), metrics in by_service.items():
        with contextlib.suppress(livestatus.MKLivestatusNotFoundError):
            for (metric_name, consolidation_function, scale), (
                start,
                end,
                step,
                values,
            ) in _fetch_rrd_data(
                site,
                host_name,
                service_description,
                metrics,
                graph_recipe.consolidation_function,
                graph_data_range,
            ):
                rrd_data[
                    RRDDataKey(
                        site,
                        host_name,
                        service_description,
                        metric_name,
                        consolidation_function,
                        scale,
                    )
                ] = TimeSeries(
                    start=start,
                    end=end,
                    step=step,
                    values=values,
                    conversion=conversion,
                )
    _align_and_resample_rrds(rrd_data, graph_recipe.consolidation_function)
    _chop_last_empty_step(graph_data_range, rrd_data)

    return rrd_data


def _align_and_resample_rrds(
    rrd_data: RRDData, consolidation_function: GraphConsolidationFunction | None
) -> None:
    """RRDTool aligns start/end/step to its internal precision.

    This is returned as first 3 values in each RRD data row. Using that
    info resampling and alignment is done in reference to the first metric.

    TimeSeries are mutated in place, argument rrd_data is thus mutated"""
    time_window = None
    for key, time_series in rrd_data.items():
        if not time_series:
            spec_title = f"{key.host_name}/{key.service_name}/{key.metric_name}"
            raise MKGeneralException(_("Cannot get RRD data for %s") % spec_title)

        if time_window is None:
            time_window = (time_series.start, time_series.end, time_series.step)
        elif time_window != (time_series.start, time_series.end, time_series.step):
            time_series.values = (
                time_series.downsample(
                    start=time_window[0],
                    end=time_window[1],
                    step=time_window[2],
                    cf=key.consolidation_function or consolidation_function,
                )
                if time_window[2] >= time_series.step
                else time_series.forward_fill_resample(
                    start=time_window[0],
                    end=time_window[1],
                    step=time_window[2],
                )
            )


# The idea is to omit the empty last step of graphs which are showing the
# last data which ends now (at the current time) where there is not yet
# data available for the current RRD step. Showing an empty space on the
# right of the graph seems a bit odd, so strip of the last (empty) step.
#
# This makes only sense for graphs which are ending "now". So disable this
# for the other graphs.
def _chop_last_empty_step(graph_data_range: GraphDataRange, rrd_data: RRDData) -> None:
    if not rrd_data:
        return

    sample_data = next(iter(rrd_data.values()))
    step = sample_data.step
    # Disable graph chop for graphs which do not end within the current step
    if abs(time.time() - graph_data_range.time_range[1]) > step:
        return

    # To avoid a gap when querying:
    # Chop one step from the end of the graph
    # `if` that is None for *all* curves(TimeSeries or graphs).
    if all(len(graph) and graph[-1] is None for graph in rrd_data.values()):
        _chop_end_of_the_curve(rrd_data, step)


def _chop_end_of_the_curve(rrd_data: RRDData, step: int) -> None:
    for data in rrd_data.values():
        data.values = data.values[:-1]
        data.end -= step


MetricProperties = tuple[str, GraphConsolidationFunction | None, float]


def _group_needed_rrd_data_by_service(
    rrd_data_keys: Iterable[RRDDataKey],
) -> dict[
    tuple[SiteId, HostName, ServiceName],
    set[MetricProperties],
]:
    by_service: dict[
        tuple[SiteId, HostName, ServiceName],
        set[MetricProperties],
    ] = collections.defaultdict(set)
    for key in rrd_data_keys:
        by_service[(key.site_id, key.host_name, key.service_name)].add(
            (key.metric_name, key.consolidation_function, key.scale)
        )
    return by_service


def _fetch_rrd_data(
    site: SiteId,
    host_name: HostName,
    service_description: ServiceName,
    metrics: set[MetricProperties],
    consolidation_function: GraphConsolidationFunction | None,
    graph_data_range: GraphDataRange,
) -> list[tuple[MetricProperties, tuple[int, int, int, TimeSeriesValues]]]:
    start_time, end_time = graph_data_range.time_range

    step = graph_data_range.step
    # assumes str step is well formatted, colon separated step length & rrd point count
    if not isinstance(step, str):
        step = max(1, step)

    point_range = ":".join(map(str, (start_time, end_time, step)))
    lql_columns = list(rrd_columns(metrics, consolidation_function, point_range))
    query = livestatus_lql([host_name], lql_columns, service_description)

    with sites.only_sites(site):
        data = sites.live().query_row(query)

    return list(zip(metrics, [(int(d[0]), int(d[1]), int(d[2]), d[3:]) for d in data]))


def rrd_columns(
    metrics: Iterable[MetricProperties],
    consolidation_function: GraphConsolidationFunction | None,
    data_range: str,
) -> Iterator[ColumnName]:
    """RRD data columns for each metric

    Include scaling of metric directly in query"""

    for perfvar, cf, scale in metrics:
        cf = consolidation_function or cf or "max"
        rpn = f"{perfvar}.{cf}"
        if scale != 1.0:
            rpn += ",%f,*" % scale
        yield f"rrddata:{perfvar}:{rpn}:{data_range}"


def _reverse_translate_into_all_potentially_relevant_metrics(
    canonical_name: MetricName,
    current_version: int,
    translations: Iterable[Mapping[MetricName, CheckMetricEntry]],
) -> set[MetricName]:
    return {
        canonical_name,
        *(
            metric_name
            for trans in translations
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
def _reverse_translate_into_all_potentially_relevant_metrics_cached(
    canonical_name: MetricName,
) -> set[MetricName]:
    return _reverse_translate_into_all_potentially_relevant_metrics(
        canonical_name,
        parse_check_mk_version(cmk_version.__version__),
        check_metrics.values(),
    )


def all_rrd_columns_potentially_relevant_for_metric(
    metric_name: MetricName,
    consolidation_function: GraphConsolidationFunction,
    from_time: int,
    until_time: int,
) -> Iterator[ColumnName]:
    yield from rrd_columns(
        (
            (
                metric_name,
                None,
                # at this point, we do not yet know if there any potential scalings due to metric
                # translations
                1,
            )
            for metric_name in _reverse_translate_into_all_potentially_relevant_metrics_cached(
                metric_name
            )
        ),
        consolidation_function,
        f"{from_time}:{until_time}:60",
    )


def translate_and_merge_rrd_columns(
    target_metric: MetricName,
    rrd_columms: Iterable[tuple[str, TimeSeriesValues]],
    translations: Mapping[MetricName, TranslationSpec],
    registered_metrics: Mapping[str, RegisteredMetric],
) -> TimeSeries:
    def scaler(scale: float) -> Callable[[float], float]:
        return lambda v: v * scale

    relevant_ts = []

    for column_name, data in rrd_columms:
        if data is None:
            raise MKGeneralException(_("Cannot retrieve historic data with Nagios core"))
        if len(data) <= 3:
            continue

        metric_name = MetricName(column_name.split(":")[1])
        metric_translation = find_matching_translation(metric_name, translations)

        if metric_translation.name == target_metric:
            if not data or data[0] is None or data[1] is None or data[2] is None:
                raise ValueError(data)
            relevant_ts.append(
                TimeSeries(
                    start=int(data[0]),
                    end=int(data[1]),
                    step=int(data[2]),
                    values=data[3:],
                    conversion=scaler(metric_translation.scale),
                )
            )

    if not relevant_ts:
        return TimeSeries(start=0, end=0, step=0, values=[])

    timeseries = relevant_ts[0]
    _op_title, op_func = time_series_operators()["MERGE"]
    single_value_series = [op_func_wrapper(op_func, list(tsp)) for tsp in zip(*relevant_ts)]

    return TimeSeries(
        start=timeseries.start,
        end=timeseries.end,
        step=timeseries.step,
        values=single_value_series,
        conversion=user_specific_unit(
            get_metric_spec(
                metric_name,
                registered_metrics,
            ).unit_spec,
            user,
            active_config,
        ).conversion,
    )
