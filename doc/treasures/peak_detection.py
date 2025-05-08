#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import argparse
import dataclasses
import json
import logging
import os
import statistics
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from itertools import compress
from typing import Any, Literal, NamedTuple

import livestatus

from cmk.livestatus_client import (  # type: ignore[attr-defined]
    SingleSiteConnection,
    SiteId,
)


@dataclass
class QueryArgs:
    hostname: str | None
    service_descr: str
    metric_name: str
    start_time: int
    end_time: int
    liveproxy_sites: Sequence[SiteId] | None = None
    extra_metrics: Sequence[str] | None = None


@dataclass
class Timeseries:
    values: Sequence[float]
    timestamps: Sequence[int]


@dataclass
class QueriedData:
    host_name: str
    service_descr: str
    metric_name: str
    avg_data: Timeseries
    min_data: Timeseries
    max_data: Timeseries
    site_id: SiteId
    extra_metrics: list[tuple[str, tuple[Timeseries, Timeseries, Timeseries]]]


class Incident(NamedTuple):
    timestamp: int
    value: float
    extra_metric_info: list[tuple[str, tuple[float, float, float]]]

    def __str__(self) -> str:
        return f"{_from_timestamp(self.timestamp)}: {self.value:.5f} {self.extra_metric_info}"


@dataclass
class Anomaly:
    site_id: SiteId
    host_name: str
    service_descr: str
    metric_name: str
    mean: float
    median: float
    anomalies: Sequence[Incident]


class LiveproxydConnection(SingleSiteConnection):
    def __init__(self, site_id: str, *args: Any, **kwargs: Any) -> None:
        if (omd_root := os.getenv("OMD_ROOT")) is None:
            raise ValueError("Script needs to be run in site context")

        super().__init__(
            "unix:" + omd_root + "/tmp/run/liveproxy/" + site_id,  # nosec B108 # BNS:7a2427
            SiteId(site_id),
            *args,
            **kwargs,
        )


def _query_livestatus(query: str) -> Sequence[Sequence[Any]]:
    connection = livestatus.LocalConnection()
    connection.set_timeout(5)
    return connection.query(query)


def _query_liveproxyd(site_id: SiteId, query: str) -> Sequence[Sequence[Any]]:
    connection = LiveproxydConnection(site_id)
    connection.set_timeout(5)
    query += "OutputFormat: json\nKeepAlive: on\nResponseHeader: fixed16\n\n"
    return connection.query(query)


def _get_query(query_args: QueryArgs) -> str:
    query_lines = ["GET services", f"Filter: service_description = {query_args.service_descr}"]
    if query_args.hostname is not None:
        query_lines.append(f"Filter: host_name = {query_args.hostname}")

    step = 1
    metric_columns = []
    for metric_name in [query_args.metric_name] + list(query_args.extra_metrics or []):
        metric_columns.append(
            f"rrddata:m1:{metric_name}.average:{query_args.start_time}:{query_args.end_time}:{step}"
        )
        metric_columns.append(
            f"rrddata:m1:{metric_name}.min:{query_args.start_time}:{query_args.end_time}:{step}"
        )
        metric_columns.append(
            f"rrddata:m1:{metric_name}.max:{query_args.start_time}:{query_args.end_time}:{step}"
        )
    query_lines.append(f"Columns: host_name description {' '.join(metric_columns)}")
    query_lines.append("")

    logging.debug("Query: %s", "\n".join(query_lines))
    return "\n".join(query_lines)


def _parse_response(response_line: Sequence[Any]) -> Timeseries:
    def _validity_mask(val: Any) -> bool:
        try:
            float(val)
            return True
        except (TypeError, ValueError):
            return False

    start, end, interval = response_line[0:3]
    data_raw = response_line[3:]
    mask = [_validity_mask(d) for d in data_raw]
    times = [start + i * interval for i in range(len(data_raw))]
    data_numeric = list(compress(data_raw, mask))
    return Timeseries([float(d) for d in data_numeric], list(compress(times, mask)))


def _get_metric_data(query_args: QueryArgs) -> Sequence[QueriedData]:
    responses: list[tuple[SiteId, Sequence[Sequence[Any]]]] = []
    if query_args.liveproxy_sites:
        for site_id in query_args.liveproxy_sites:
            responses.append((site_id, _query_liveproxyd(site_id, _get_query(query_args))))
    else:
        responses.append((SiteId("local"), _query_livestatus(_get_query(query_args))))

    hosts = []
    for site_id, response in responses:
        for host_data in response:
            host_name = str(host_data[0])
            service_descr = str(host_data[1])
            avg_data = _parse_response(host_data[2])
            min_data = _parse_response(host_data[3])
            max_data = _parse_response(host_data[4])
            extra_metrics: list[tuple[str, tuple[Timeseries, Timeseries, Timeseries]]] = []
            for extra_metric in query_args.extra_metrics or []:
                extra_avg = _parse_response(host_data[5])
                extra_min = _parse_response(host_data[6])
                extra_max = _parse_response(host_data[7])
                extra_metrics.append((extra_metric, (extra_avg, extra_min, extra_max)))
            hosts.append(
                QueriedData(
                    host_name,
                    service_descr,
                    query_args.metric_name,
                    avg_data,
                    min_data,
                    max_data,
                    site_id,
                    extra_metrics,
                )
            )
    return hosts


def _create_incident(
    timestamp: int,
    value: float,
    extra_metrics: list[tuple[str, tuple[Timeseries, Timeseries, Timeseries]]],
) -> Incident:
    extra_metric_info = []
    for metric_name, (avg_data, min_data, max_data) in extra_metrics:
        incident_index = avg_data.timestamps.index(timestamp)
        extra_metric_info.append(
            (
                metric_name,
                (
                    avg_data.values[incident_index],
                    min_data.values[incident_index],
                    max_data.values[incident_index],
                ),
            )
        )
    return Incident(timestamp, value, extra_metric_info)


def _detect_anomalies_simple(
    data: Sequence[QueriedData], threshold: float, direction: Literal["upper", "lower"]
) -> Sequence[Anomaly]:
    anomalies = []

    for host_data in data:
        logging.debug("Host data: %s", host_data)
        try:
            median = statistics.median(host_data.avg_data.values)
        except statistics.StatisticsError:
            logging.exception("Error calculating median, ignoring host '%s'", host_data.host_name)
            continue
        try:
            mean = statistics.mean(host_data.avg_data.values)
        except statistics.StatisticsError:
            logging.exception("Error calculating mean, ignoring host '%s'", host_data.host_name)
            continue

        match direction:
            case "upper":
                peaks = [
                    _create_incident(t, v, host_data.extra_metrics)
                    for (t, v) in zip(host_data.max_data.timestamps, host_data.max_data.values)
                    if v > threshold
                ]
            case "lower":
                peaks = [
                    _create_incident(t, v, host_data.extra_metrics)
                    for (t, v) in zip(host_data.min_data.timestamps, host_data.min_data.values)
                    if v < threshold
                ]
            case _:
                raise ValueError(f"Invalid direction: {direction}")

        if peaks:
            anomalies.append(
                Anomaly(
                    host_data.site_id,
                    host_data.host_name,
                    host_data.service_descr,
                    host_data.metric_name,
                    mean,
                    median,
                    peaks,
                )
            )
    return anomalies


def _to_timestamp(time_str: str) -> int:
    return int(datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").timestamp())


def _from_timestamp(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def _format_output(anomalies: Sequence[Anomaly], formatter: Literal["human", "json"]) -> str:
    match formatter:
        case "human":
            output = ""
            for anomaly in anomalies:
                input_args = (
                    f"\n{'Site:':<10}{anomaly.site_id}\n{'Hostname:':<10}{anomaly.host_name}"
                    f"\n{'Service:':<10}{anomaly.service_descr}\n{'Metric:':<10}{anomaly.metric_name}"
                )
                formatted_anomalies = [str(i) for i in anomaly.anomalies]
                output += "\n".join(
                    [
                        input_args,
                        f"{'Mean:':<10}{anomaly.mean:.5f}",
                        f"{'Median:':<10}{anomaly.median:.5f}",
                        f"Anomalies:\n {'\n '.join(formatted_anomalies)}\n",
                    ]
                )
        case "json":
            results = [dataclasses.asdict(anomaly) for anomaly in anomalies]
            output = json.dumps(results, indent=4)
        case other:
            raise NotImplementedError(f"Formatter {other} not implemented")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hostname", help="Hostname to query")
    parser.add_argument("--service", default="Check_MK", help="Service description to query")
    parser.add_argument("--metric", default="execution_time", help="Metric name to query")
    parser.add_argument(
        "--start",
        required=True,
        help="Start time (YYYY-MM-DD HH:MM:SS) of range to detect anomalies",
    )
    parser.add_argument(
        "--end", required=True, help="End time (YYYY-MM-DD HH:MM:SS) of range to detect anomalies"
    )
    parser.add_argument(
        "--simple_thresh",
        type=float,
        help="Simple threshold. Values above/below this(depending on configured direction) are detected as anomalies",
    )
    parser.add_argument(
        "--direction",
        choices=["upper", "lower"],
        default="upper",
        help="Whether to detect upper or lower anomalies",
    )
    parser.add_argument(
        "--formatter", choices=["human", "json"], default="human", help="Output format"
    )
    parser.add_argument("--liveproxyd_sites", help="List of liveproxyd sites to query", nargs="+")
    parser.add_argument(
        "--extra_metrics",
        help="List of extra metrics. These are not used in the computation",
        nargs="+",
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        default="NOTSET",
        choices=["CRITICAL", "FATAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"],
        help="Override the configured logging level",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.getLevelNamesMapping()[args.log_level],
        format="%(message)s",
        stream=sys.stdout,
    )

    start_time = _to_timestamp(args.start)
    end_time = _to_timestamp(args.end)
    query_args = QueryArgs(
        args.hostname,
        args.service,
        args.metric,
        start_time,
        end_time,
        args.liveproxyd_sites,
        args.extra_metrics,
    )

    queried_data = _get_metric_data(query_args)
    anomalies = _detect_anomalies_simple(queried_data, args.simple_thresh, args.direction)

    output = _format_output(anomalies, args.formatter)
    logging.info("Incidents: %s", output)


if __name__ == "__main__":
    main()
