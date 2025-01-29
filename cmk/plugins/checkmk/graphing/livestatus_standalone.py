#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())
UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))

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
