#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())
UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_UNUSED = metrics.Unit(metrics.DecimalNotation(""))

metric_forks = metrics.Metric(
    name="forks",
    title=Title("Forks"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_BROWN,
)

metric_site_cert_days = metrics.Metric(
    name="site_cert_days",
    title=Title("Certificate age"),
    unit=UNIT_TIME,
    color=metrics.Color.GREEN,
)

metric_host_check_rate = metrics.Metric(
    name="host_check_rate",
    title=Title("Host check rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

metric_service_check_rate = metrics.Metric(
    name="service_check_rate",
    title=Title("Service check rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

metric_monitored_hosts = metrics.Metric(
    name="monitored_hosts",
    title=Title("Monitored hosts"),
    unit=UNIT_NUMBER,
    color=metrics.Color.BLUE,
)

metric_monitored_services = metrics.Metric(
    name="monitored_services",
    title=Title("Monitored services"),
    unit=UNIT_NUMBER,
    color=metrics.Color.GREEN,
)

metric_livestatus_request_rate = metrics.Metric(
    name="livestatus_request_rate",
    title=Title("Livestatus requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

metric_livestatus_connect_rate = metrics.Metric(
    name="livestatus_connect_rate",
    title=Title("Livestatus connects"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)

metric_helper_usage_fetcher = metrics.Metric(
    name="helper_usage_fetcher",
    title=Title("Fetcher helper usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_YELLOW,
)

metric_helper_usage_checker = metrics.Metric(
    name="helper_usage_checker",
    title=Title("Checker helper usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)

metric_helper_usage_generic = metrics.Metric(
    name="helper_usage_generic",
    title=Title("Active check helper usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)

metric_average_latency_cmk = metrics.Metric(
    name="average_latency_cmk",
    title=Title("Checkmk checker latency"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)

metric_average_latency_fetcher = metrics.Metric(
    name="average_latency_fetcher",
    title=Title("Checkmk fetcher latency"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_YELLOW,
)

metric_average_latency_generic = metrics.Metric(
    name="average_latency_generic",
    title=Title("Active check latency"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)

metric_livestatus_usage = metrics.Metric(
    name="livestatus_usage",
    title=Title("Livestatus usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)

metric_livestatus_overflows_rate = metrics.Metric(
    name="livestatus_overflows_rate",
    title=Title("Livestatus overflows"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)

metric_log_message_rate = metrics.Metric(
    name="log_message_rate",
    title=Title("Log messages"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)

metric_perf_data_count_rate = metrics.Metric(
    name="perf_data_count_rate",
    title=Title("Rate of performance data received"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_metrics_count_rate = metrics.Metric(
    name="metrics_count_rate",
    title=Title("Rate of metrics received"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_influxdb_queue_usage = metrics.Metric(
    name="influxdb_queue_usage",
    title=Title("InfluxDB queue usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)

metric_influxdb_queue_usage_rate = metrics.Metric(
    name="influxdb_queue_usage_rate",
    title=Title("InfluxDB queue usage rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_influxdb_overflows_rate = metrics.Metric(
    name="influxdb_overflows_rate",
    title=Title("Rate of performance data loss for InfluxDB"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_influxdb_bytes_sent_rate = metrics.Metric(
    name="influxdb_bytes_sent_rate",
    title=Title("Rate of bytes sent to the InfluxDB connection"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_rrdcached_queue_usage = metrics.Metric(
    name="rrdcached_queue_usage",
    title=Title("RRD queue usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)

metric_rrdcached_queue_usage_rate = metrics.Metric(
    name="rrdcached_queue_usage_rate",
    title=Title("RRD queue usage rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_rrdcached_overflows_rate = metrics.Metric(
    name="rrdcached_overflows_rate",
    title=Title("Rate of performance data loss for RRD"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_rrdcached_bytes_sent_rate = metrics.Metric(
    name="rrdcached_bytes_sent_rate",
    title=Title("Rate of bytes sent to the RRD connection"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_carbon_queue_usage = metrics.Metric(
    name="carbon_queue_usage",
    title=Title("Carbon queue usage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)

metric_carbon_queue_usage_rate = metrics.Metric(
    name="carbon_queue_usage_rate",
    title=Title("Carbon queue usage rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_carbon_overflows_rate = metrics.Metric(
    name="carbon_overflows_rate",
    title=Title("Rate of performance data loss for Carbon"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)

metric_carbon_bytes_sent_rate = metrics.Metric(
    name="carbon_bytes_sent_rate",
    title=Title("Rate of bytes sent to the Carbon connection"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)

perfometer_service_check_rate_host_check_rate = perfometers.Stacked(
    name="service_check_rate_host_check_rate",
    lower=perfometers.Perfometer(
        name="service_check_rate",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(400)),
        segments=["service_check_rate"],
    ),
    upper=perfometers.Perfometer(
        name="host_check_rate",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Open(90)),
        segments=["host_check_rate"],
    ),
)

graph_livestatus_requests_per_connection = graphs.Graph(
    name="livestatus_requests_per_connection",
    title=Title("Livestatus requests per connection"),
    compound_lines=[
        metrics.Fraction(
            Title("Average requests per connection"),
            UNIT_NUMBER,
            metrics.Color.DARK_YELLOW,
            dividend="livestatus_request_rate",
            divisor=metrics.Sum(
                Title("Average requests per connection"),
                metrics.Color.GRAY,
                [
                    "livestatus_connect_rate",
                    metrics.Constant(
                        Title(""),
                        UNIT_UNUSED,
                        metrics.Color.GRAY,
                        1e-16,
                    ),
                ],
            ),
        )
    ],
)

graph_livestatus_usage = graphs.Graph(
    name="livestatus_usage",
    title=Title("Livestatus usage"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    compound_lines=["livestatus_usage"],
)

graph_helper_usage = graphs.Graph(
    name="helper_usage",
    title=Title("Helper usage"),
    minimal_range=graphs.MinimalRange(
        0,
        100,
    ),
    simple_lines=[
        "helper_usage_fetcher",
        "helper_usage_checker",
        "helper_usage_generic",
    ],
)

graph_average_helper_latency = graphs.Graph(
    name="average_helper_latency",
    title=Title("Average helper latency"),
    simple_lines=[
        "average_latency_fetcher",
        "average_latency_cmk",
        "average_latency_generic",
    ],
)

graph_host_and_service_checks = graphs.Graph(
    name="host_and_service_checks",
    title=Title("Host and service checks"),
    simple_lines=[
        "host_check_rate",
        "service_check_rate",
    ],
)

graph_number_of_monitored_hosts_and_services = graphs.Graph(
    name="number_of_monitored_hosts_and_services",
    title=Title("Number of monitored hosts and services"),
    simple_lines=[
        "monitored_hosts",
        "monitored_services",
    ],
)

graph_livestatus_connects_and_requests = graphs.Graph(
    name="livestatus_connects_and_requests",
    title=Title("Livestatus connects and requests"),
    simple_lines=[
        "livestatus_request_rate",
        "livestatus_connect_rate",
    ],
)
