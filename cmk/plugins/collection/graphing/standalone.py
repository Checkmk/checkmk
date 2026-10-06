#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_DECIBEL_MILLIWATTS = metrics.Unit(metrics.DecimalNotation("dBm"))
UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))
UNIT_EURO = metrics.Unit(metrics.DecimalNotation("€"), metrics.StrictPrecision(2))
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_HERTZ = metrics.Unit(metrics.DecimalNotation("Hz"))
UNIT_TIME = metrics.Unit(metrics.TimeNotation())

metric_service_costs_eur = metrics.Metric(
    name="service_costs_eur",
    title=Title("Service Costs per Day"),
    unit=UNIT_EURO,
    color=metrics.Color.BLUE,
)
metric_num_topics = metrics.Metric(
    name="num_topics",
    title=Title("Number of topics live"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_sms_spend = metrics.Metric(
    name="sms_spend",
    title=Title("SMS spending"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_accepted = metrics.Metric(
    name="accepted",
    title=Title("Accepted connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_failed_requests = metrics.Metric(
    name="failed_requests",
    title=Title("Failed requests"),
    unit=UNIT_COUNTER,
    color=metrics.Color.CYAN,
)
metric_active = metrics.Metric(
    name="active",
    title=Title("Active connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_apply_lag = metrics.Metric(
    name="apply_lag",
    title=Title("Apply lag"),
    unit=UNIT_TIME,
    color=metrics.Color.YELLOW,
)
metric_hops = metrics.Metric(
    name="hops",
    title=Title("Number of hops"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_GRAY,
)
# TODO: Metric names with preceeding numbers seems not to be capable
# of adding scalars with graph_info (e.g. for horizontal warning levels)
metric_connections_failed_rate = metrics.Metric(
    name="connections_failed_rate",
    title=Title("Failed connections per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_failed_connections = metrics.Metric(
    name="failed_connections",
    title=Title("Failed connections"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_connections_rate = metrics.Metric(
    name="connections_rate",
    title=Title("Connections per second"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GRAY,
)
metric_p2s_bandwidth = metrics.Metric(
    name="p2s_bandwidth",
    title=Title("Point-to-site bandwidth"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_s2s_bandwidth = metrics.Metric(
    name="s2s_bandwidth",
    title=Title("Site-to-site bandwidth"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
# “Output Queue Length is the length of the output packet queue (in
# packets). If this is longer than two, there are delays and the bottleneck
# should be found and eliminated, if possible.
metric_channel_utilization = metrics.Metric(
    name="channel_utilization",
    title=Title("Channel utilization"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.YELLOW,
)
metric_response_size = metrics.Metric(
    name="response_size",
    title=Title("Response size"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_GRAY,
)
# time_http_headers/time_http_body come from check_httpv2 and correspond
# to time_headers/time_transfer from the old check_http.
# We keep the old metrics as long as the old check_http is still in use.
metric_time_http_headers = metrics.Metric(
    name="time_http_headers",
    title=Title("Time to fetch HTTP headers"),
    unit=UNIT_TIME,
    color=metrics.Color.ORANGE,
)
metric_time_http_body = metrics.Metric(
    name="time_http_body",
    title=Title("Time to fetch page content"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_error_rate = metrics.Metric(
    name="error_rate",
    title=Title("Error rate"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_avg_response_time = metrics.Metric(
    name="avg_response_time",
    title=Title("Average response time"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_BLUE,
)
metric_dtu_percent = metrics.Metric(
    name="dtu_percent",
    title=Title("Database throughput unit"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_BLUE,
)
metric_byte_count = metrics.Metric(
    name="byte_count",
    title=Title("Byte count"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_allocated_snat_ports = metrics.Metric(
    name="allocated_snat_ports",
    title=Title("Allocated SNAT ports"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_used_snat_ports = metrics.Metric(
    name="used_snat_ports",
    title=Title("Used SNAT ports"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_BLUE,
)
metric_power_usage_percentage = metrics.Metric(
    name="power_usage_percentage",
    title=Title("Power usage percentage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_PINK,
)
metric_frequency = metrics.Metric(
    name="frequency",
    title=Title("Frequency"),
    unit=UNIT_HERTZ,
    color=metrics.Color.PURPLE,
)
metric_port_temp_0 = metrics.Metric(
    name="port_temp_0",
    title=Title("Temperature Lane 1"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.CYAN,
)
metric_port_temp_1 = metrics.Metric(
    name="port_temp_1",
    title=Title("Temperature Lane 2"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.DARK_YELLOW,
)
metric_port_temp_2 = metrics.Metric(
    name="port_temp_2",
    title=Title("Temperature Lane 3"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.DARK_PINK,
)
metric_port_temp_3 = metrics.Metric(
    name="port_temp_3",
    title=Title("Temperature Lane 4"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.DARK_BLUE,
)
metric_port_temp_4 = metrics.Metric(
    name="port_temp_4",
    title=Title("Temperature Lane 5"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.BLUE,
)
metric_port_temp_5 = metrics.Metric(
    name="port_temp_5",
    title=Title("Temperature Lane 6"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.YELLOW,
)
metric_port_temp_6 = metrics.Metric(
    name="port_temp_6",
    title=Title("Temperature Lane 7"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_port_temp_7 = metrics.Metric(
    name="port_temp_7",
    title=Title("Temperature Lane 8"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.PURPLE,
)
metric_port_temp_8 = metrics.Metric(
    name="port_temp_8",
    title=Title("Temperature Lane 9"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.CYAN,
)
metric_port_temp_9 = metrics.Metric(
    name="port_temp_9",
    title=Title("Temperature Lane 10"),
    unit=UNIT_DECIBEL_MILLIWATTS,
    color=metrics.Color.DARK_YELLOW,
)
metric_lifetime_remaining = metrics.Metric(
    name="lifetime_remaining",
    title=Title("Lifetime remaining"),
    unit=UNIT_TIME,
    color=metrics.Color.DARK_YELLOW,
)
metric_ingress_packet_drop = metrics.Metric(
    name="ingress_packet_drop",
    title=Title("Ingress packet drop"),
    unit=UNIT_COUNTER,
    color=metrics.Color.YELLOW,
)
metric_egress_packet_drop = metrics.Metric(
    name="egress_packet_drop",
    title=Title("Egress packet drop"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_log_files_used = metrics.Metric(
    name="log_files_used",
    title=Title("Used size of log files"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_log_files_total = metrics.Metric(
    name="log_files_total",
    title=Title("Total size of log files"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)
metric_mem_available = metrics.Metric(
    name="mem_available",
    title=Title("Estimated RAM for new processes"),
    unit=UNIT_BYTES,
    color=metrics.Color.YELLOW,
)
metric_swap_used_percent = metrics.Metric(
    name="swap_used_percent",
    title=Title("Swap used percentage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.DARK_GREEN,
)
metric_caches = metrics.Metric(
    name="caches",
    title=Title("Memory used by caches"),
    unit=UNIT_BYTES,
    color=metrics.Color.DARK_GRAY,
)
metric_mem_lnx_total_used = metrics.Metric(
    name="mem_lnx_total_used",
    title=Title("Total used memory"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_mem_fragmentation = metrics.Metric(
    name="mem_fragmentation",
    title=Title("Memory fragmentation"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_ORANGE,
)
metric_evictions = metrics.Metric(
    name="evictions",
    title=Title("Evictions"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_CYAN,
)
metric_reclaimed = metrics.Metric(
    name="reclaimed",
    title=Title("Reclaimed"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_backup_avgspeed = metrics.Metric(
    name="backup_avgspeed",
    title=Title("Average speed of backup"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_backup_duration = metrics.Metric(
    name="backup_duration",
    title=Title("Duration of backup"),
    unit=UNIT_TIME,
    color=metrics.Color.CYAN,
)
metric_backup_age_differential_partial = metrics.Metric(
    name="backup_age_differential_partial",
    title=Title("Age of last differential partial backup"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_storage_percent = metrics.Metric(
    name="storage_percent",
    title=Title("Storage space used percentage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BLUE,
)
metric_memory_used = metrics.Metric(
    name="memory_used",
    title=Title("Memory used"),
    unit=UNIT_BYTES,
    color=metrics.Color.PURPLE,
)
# In order to use the "bytes" unit we would have to change the output of the check, (i.e. divide by
# 1024) which means an invalidation of historic values.
metric_serverlog_storage_percent = metrics.Metric(
    name="serverlog_storage_percent",
    title=Title("Server log storage used"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.PURPLE,
)
metric_hosts_healthy = metrics.Metric(
    name="hosts_healthy",
    title=Title("Healthy hosts"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_age_oldest = metrics.Metric(
    name="age_oldest",
    title=Title("Oldest age"),
    unit=UNIT_TIME,
    color=metrics.Color.BLUE,
)
metric_fs_provisioning = metrics.Metric(
    name="fs_provisioning",
    title=Title("Provisioned space"),
    unit=UNIT_BYTES,
    color=metrics.Color.ORANGE,
)
metric_util5 = metrics.Metric(
    name="util5",
    title=Title("CPU utilization last 5 minutes"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_GREEN,
)
metric_cpu_time_percent = metrics.Metric(
    name="cpu_time_percent",
    title=Title("CPU time percentage"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.BROWN,
)
metric_failed_jobs = metrics.Metric(
    name="failed_jobs",
    title=Title("Total number of failed jobs"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_zombie_jobs = metrics.Metric(
    name="zombie_jobs",
    title=Title("Total number of zombie jobs"),
    unit=UNIT_COUNTER,
    color=metrics.Color.ORANGE,
)
metric_cpu_percent = metrics.Metric(
    name="cpu_percent",
    title=Title("CPU used"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.ORANGE,
)
