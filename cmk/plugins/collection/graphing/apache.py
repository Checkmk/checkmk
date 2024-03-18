#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title, translations

translation_apache_status = translations.Translation(
    name="apache_status",
    check_commands=[translations.PassiveCheck("apache_status")],
    translations={
        "Uptime": translations.RenameTo("uptime"),
        "IdleWorkers": translations.RenameTo("idle_workers"),
        "BusyWorkers": translations.RenameTo("busy_workers"),
        "IdleServers": translations.RenameTo("idle_servers"),
        "BusyServers": translations.RenameTo("busy_servers"),
        "OpenSlots": translations.RenameTo("open_slots"),
        "TotalSlots": translations.RenameTo("total_slots"),
        "CPULoad": translations.RenameTo("load1"),
        "ReqPerSec": translations.RenameTo("requests_per_second"),
        "BytesPerSec": translations.RenameTo("data_transfer_rate"),
        "BytesPerReq": translations.RenameTo("request_transfer_rate"),
        "ConnsTotal": translations.RenameTo("connections"),
        "ConnsAsyncWriting": translations.RenameTo("connections_async_writing"),
        "ConnsAsyncKeepAlive": translations.RenameTo("connections_async_keepalive"),
        "ConnsAsyncClosing": translations.RenameTo("connections_async_closing"),
        "State_StartingUp": translations.RenameTo("apache_state_startingup"),
        "State_Waiting": translations.RenameTo("apache_state_waiting"),
        "State_Logging": translations.RenameTo("apache_state_logging"),
        "State_DNS": translations.RenameTo("apache_state_dns"),
        "State_SendingReply": translations.RenameTo("apache_state_sending_reply"),
        "State_ReadingRequest": translations.RenameTo("apache_state_reading_request"),
        "State_Closing": translations.RenameTo("apache_state_closing"),
        "State_IdleCleanup": translations.RenameTo("apache_state_idle_cleanup"),
        "State_Finishing": translations.RenameTo("apache_state_finishing"),
        "State_Keepalive": translations.RenameTo("apache_state_keep_alive"),
    },
)

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_apache_state_startingup = metrics.Metric(
    name="apache_state_startingup",
    title=Title("Starting up"),
    unit=UNIT_NUMBER,
    color=metrics.Color.PURPLE,
)

metric_apache_state_waiting = metrics.Metric(
    name="apache_state_waiting",
    title=Title("Waiting"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,
)

metric_apache_state_logging = metrics.Metric(
    name="apache_state_logging",
    title=Title("Logging"),
    unit=UNIT_NUMBER,
    color=metrics.Color.YELLOW,
)

metric_apache_state_dns = metrics.Metric(
    name="apache_state_dns",
    title=Title("DNS lookup"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_apache_state_sending_reply = metrics.Metric(
    name="apache_state_sending_reply",
    title=Title("Sending reply"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_CYAN,
)

metric_apache_state_reading_request = metrics.Metric(
    name="apache_state_reading_request",
    title=Title("Reading request"),
    unit=UNIT_NUMBER,
    color=metrics.Color.CYAN,
)

metric_apache_state_closing = metrics.Metric(
    name="apache_state_closing",
    title=Title("Closing connection"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_apache_state_idle_cleanup = metrics.Metric(
    name="apache_state_idle_cleanup",
    title=Title("Idle cleanup of worker"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_PURPLE,
)

metric_apache_state_finishing = metrics.Metric(
    name="apache_state_finishing",
    title=Title("Gracefully finishing"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_apache_state_keep_alive = metrics.Metric(
    name="apache_state_keep_alive",
    title=Title("Keepalive"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_GRAY,
)

graph_apache_status = graphs.Graph(
    name="apache_status",
    title=Title("Apache status"),
    compound_lines=[
        "apache_state_startingup",
        "apache_state_waiting",
        "apache_state_logging",
        "apache_state_dns",
        "apache_state_sending_reply",
        "apache_state_reading_request",
        "apache_state_closing",
        "apache_state_idle_cleanup",
        "apache_state_finishing",
        "apache_state_keep_alive",
    ],
)

metric_requests_per_second = metrics.Metric(
    name="requests_per_second",
    title=Title("Requests per second"),
    unit=metrics.Unit(metrics.DecimalNotation("req/s")),
    color=metrics.Color.GRAY,
)
