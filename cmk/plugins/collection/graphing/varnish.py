#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_PERCENTAGE = metrics.Unit(metrics.DecimalNotation("%"))
UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_varnish_objects_expired_rate = metrics.Metric(
    name="varnish_objects_expired_rate",
    title=Title("Expired objects"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_varnish_objects_lru_moved_rate = metrics.Metric(
    name="varnish_objects_lru_moved_rate",
    title=Title("LRU moved objects"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_varnish_objects_lru_nuked_rate = metrics.Metric(
    name="varnish_objects_lru_nuked_rate",
    title=Title("LRU nuked objects"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_varnish_worker_thread_ratio = metrics.Metric(
    name="varnish_worker_thread_ratio",
    title=Title("Varnish Worker thread ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)
metric_varnish_worker_create_rate = metrics.Metric(
    name="varnish_worker_create_rate",
    title=Title("Worker threads created"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_varnish_worker_drop_rate = metrics.Metric(
    name="varnish_worker_drop_rate",
    title=Title("Dropped work requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_varnish_worker_failed_rate = metrics.Metric(
    name="varnish_worker_failed_rate",
    title=Title("Worker threads not created"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_varnish_worker_lqueue_rate = metrics.Metric(
    name="varnish_worker_lqueue_rate",
    title=Title("Work request queue length"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.RED,
)
metric_varnish_worker_max_rate = metrics.Metric(
    name="varnish_worker_max_rate",
    title=Title("Worker threads limited"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_varnish_worker_queued_rate = metrics.Metric(
    name="varnish_worker_queued_rate",
    title=Title("Queued work requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_varnish_worker_rate = metrics.Metric(
    name="varnish_worker_rate",
    title=Title("Worker threads"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_varnish_cache_hit_rate = metrics.Metric(
    name="varnish_cache_hit_rate",
    title=Title("Cache hits"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_varnish_cache_hitpass_rate = metrics.Metric(
    name="varnish_cache_hitpass_rate",
    title=Title("Cache hits for pass"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_varnish_cache_miss_rate = metrics.Metric(
    name="varnish_cache_miss_rate",
    title=Title("Cache misses"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_varnish_backend_success_ratio = metrics.Metric(
    name="varnish_backend_success_ratio",
    title=Title("Varnish Backend success ratio"),
    unit=UNIT_PERCENTAGE,
    color=metrics.Color.LIGHT_BLUE,
)
metric_varnish_backend_busy_rate = metrics.Metric(
    name="varnish_backend_busy_rate",
    title=Title("Backend Conn. too many"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.RED,
)
metric_varnish_backend_conn_rate = metrics.Metric(
    name="varnish_backend_conn_rate",
    title=Title("Backend Conn. success"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PINK,
)
metric_varnish_backend_fail_rate = metrics.Metric(
    name="varnish_backend_fail_rate",
    title=Title("Backend Conn. failures"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_varnish_backend_recycle_rate = metrics.Metric(
    name="varnish_backend_recycle_rate",
    title=Title("Backend Conn. recycles"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_varnish_backend_req_rate = metrics.Metric(
    name="varnish_backend_req_rate",
    title=Title("Backend Conn. requests"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.YELLOW,
)
metric_varnish_backend_retry_rate = metrics.Metric(
    name="varnish_backend_retry_rate",
    title=Title("Backend Conn. retry"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_varnish_backend_reuse_rate = metrics.Metric(
    name="varnish_backend_reuse_rate",
    title=Title("Backend Conn. reuses"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BROWN,
)
metric_varnish_backend_toolate_rate = metrics.Metric(
    name="varnish_backend_toolate_rate",
    title=Title("Backend Conn. was closed"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_varnish_backend_unhealthy_rate = metrics.Metric(
    name="varnish_backend_unhealthy_rate",
    title=Title("Backend Conn. not attempted"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)
metric_varnish_fetch_1xx_rate = metrics.Metric(
    name="varnish_fetch_1xx_rate",
    title=Title("Fetch no body (1xx)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PINK,
)
metric_varnish_fetch_204_rate = metrics.Metric(
    name="varnish_fetch_204_rate",
    title=Title("Fetch no body (204)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BROWN,
)
metric_varnish_fetch_304_rate = metrics.Metric(
    name="varnish_fetch_304_rate",
    title=Title("Fetch no body (304)"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_CYAN,
)
metric_varnish_fetch_bad_rate = metrics.Metric(
    name="varnish_fetch_bad_rate",
    title=Title("Fetch had bad headers"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_PURPLE,
)
metric_varnish_fetch_chunked_rate = metrics.Metric(
    name="varnish_fetch_chunked_rate",
    title=Title("Fetch chunked"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BROWN,
)
metric_varnish_fetch_close_rate = metrics.Metric(
    name="varnish_fetch_close_rate",
    title=Title("Fetch wanted close"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_PINK,
)
metric_varnish_fetch_eof_rate = metrics.Metric(
    name="varnish_fetch_eof_rate",
    title=Title("Fetch EOF"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_BLUE,
)
metric_varnish_fetch_failed_rate = metrics.Metric(
    name="varnish_fetch_failed_rate",
    title=Title("Fetch failed"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_PURPLE,
)
metric_varnish_fetch_head_rate = metrics.Metric(
    name="varnish_fetch_head_rate",
    title=Title("Fetch head"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_GREEN,
)
metric_varnish_fetch_length_rate = metrics.Metric(
    name="varnish_fetch_length_rate",
    title=Title("Fetch with length"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_CYAN,
)
metric_varnish_fetch_oldhttp_rate = metrics.Metric(
    name="varnish_fetch_oldhttp_rate",
    title=Title("Fetch pre HTTP/1.1 closed"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
metric_varnish_fetch_zero_rate = metrics.Metric(
    name="varnish_fetch_zero_rate",
    title=Title("Fetch zero length"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_varnish_esi_errors_rate = metrics.Metric(
    name="varnish_esi_errors_rate",
    title=Title("ESI Errors"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)
metric_varnish_esi_warnings_rate = metrics.Metric(
    name="varnish_esi_warnings_rate",
    title=Title("ESI Warnings"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_varnish_client_conn_rate = metrics.Metric(
    name="varnish_client_conn_rate",
    title=Title("Client connections accepted"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.BLUE,
)
metric_varnish_client_drop_late_rate = metrics.Metric(
    name="varnish_client_drop_late_rate",
    title=Title("Connection dropped late"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.PURPLE,
)
metric_varnish_client_drop_rate = metrics.Metric(
    name="varnish_client_drop_rate",
    title=Title("Connections dropped"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_varnish_client_req_rate = metrics.Metric(
    name="varnish_client_req_rate",
    title=Title("Client requests received"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.GREEN,
)

perfometer_varnish_worker_thread_ratio = perfometers.Perfometer(
    name="varnish_worker_thread_ratio",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100),
    ),
    segments=["varnish_worker_thread_ratio"],
)
perfometer_varnish_backend_success_ratio = perfometers.Perfometer(
    name="varnish_backend_success_ratio",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Closed(100),
    ),
    segments=["varnish_backend_success_ratio"],
)

graph_varnish_objects = graphs.Graph(
    name="varnish_objects",
    title=Title("Varnish Objects"),
    simple_lines=[
        "varnish_objects_expired_rate",
        "varnish_objects_lru_nuked_rate",
        "varnish_objects_lru_moved_rate",
    ],
)
graph_varnish_worker = graphs.Graph(
    name="varnish_worker",
    title=Title("Varnish Worker"),
    simple_lines=[
        "varnish_worker_lqueue_rate",
        "varnish_worker_create_rate",
        "varnish_worker_drop_rate",
        "varnish_worker_rate",
        "varnish_worker_failed_rate",
        "varnish_worker_queued_rate",
        "varnish_worker_max_rate",
    ],
)
graph_varnish_cache = graphs.Graph(
    name="varnish_cache",
    title=Title("Varnish Cache"),
    simple_lines=[
        "varnish_cache_miss_rate",
        "varnish_cache_hit_rate",
        "varnish_cache_hitpass_rate",
    ],
)
graph_varnish_backend_connections = graphs.Graph(
    name="varnish_backend_connections",
    title=Title("Varnish Backend Connections"),
    simple_lines=[
        "varnish_backend_busy_rate",
        "varnish_backend_unhealthy_rate",
        "varnish_backend_req_rate",
        "varnish_backend_recycle_rate",
        "varnish_backend_retry_rate",
        "varnish_backend_fail_rate",
        "varnish_backend_toolate_rate",
        "varnish_backend_conn_rate",
        "varnish_backend_reuse_rate",
    ],
)
graph_varnish_fetch = graphs.Graph(
    name="varnish_fetch",
    title=Title("Varnish Fetch"),
    simple_lines=[
        "varnish_fetch_oldhttp_rate",
        "varnish_fetch_head_rate",
        "varnish_fetch_eof_rate",
        "varnish_fetch_zero_rate",
        "varnish_fetch_304_rate",
        "varnish_fetch_length_rate",
        "varnish_fetch_failed_rate",
        "varnish_fetch_bad_rate",
        "varnish_fetch_close_rate",
        "varnish_fetch_1xx_rate",
        "varnish_fetch_chunked_rate",
        "varnish_fetch_204_rate",
    ],
)
graph_varnish_esi_errors_and_warnings = graphs.Graph(
    name="varnish_esi_errors_and_warnings",
    title=Title("Varnish ESI Errors and Warnings"),
    simple_lines=[
        "varnish_esi_errors_rate",
        "varnish_esi_warnings_rate",
    ],
)
graph_varnish_clients = graphs.Graph(
    name="varnish_clients",
    title=Title("Varnish Clients"),
    simple_lines=[
        "varnish_client_req_rate",
        "varnish_client_conn_rate",
        "varnish_client_drop_rate",
        "varnish_client_drop_late_rate",
    ],
)
