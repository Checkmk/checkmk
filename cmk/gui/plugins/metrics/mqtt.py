#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.utils import graph_info, metric_info

metric_info["connections_opened_received_rate"] = {
    "title": _("Connections opened"),
    "unit": "1/s",
    "color": "11/a",
}

metric_info["subscriptions"] = {
    "title": _("Current subscriptions"),
    "unit": "1/s",
    "color": "14/a",
}

metric_info["clients_connected"] = {
    "title": _("Clients connected"),
    "unit": "count",
    "color": "11/a",
}

metric_info["clients_maximum"] = {
    "title": _("Clients maximum"),
    "unit": "count",
    "color": "14/a",
}

metric_info["clients_total"] = {
    "title": _("Clients total"),
    "unit": "count",
    "color": "21/a",
}

graph_info["mqtt_clients"] = {
    "title": _("Clients"),
    "metrics": [
        ("clients_connected", "line"),
        ("clients_maximum", "line"),
        ("clients_total", "line"),
    ],
    "optional_metrics": [
        "clients_maximum",
    ],
}

metric_info["bytes_received_rate"] = {
    "title": _("Bytes received"),
    "unit": "bytes/s",
    "color": "#00e060",
}

metric_info["bytes_sent_rate"] = {
    "title": _("Bytes sent"),
    "unit": "bytes/s",
    "color": "#0080e0",
}

graph_info["bytes_transmitted"] = {
    "title": _("Bytes sent/received"),
    "metrics": [
        ("bytes_sent_rate", "-area"),
        ("bytes_received_rate", "area"),
    ],
}

metric_info["messages_received_rate"] = {
    "title": _("Messages received"),
    "unit": "1/s",
    "color": "#00ffc0",
}

metric_info["messages_sent_rate"] = {
    "title": _("Messages sent"),
    "unit": "1/s",
    "color": "#00c0ff",
}

graph_info["messages_transmitted"] = {
    "title": _("Messages sent/received"),
    "metrics": [
        ("messages_sent_rate", "-area"),
        ("messages_received_rate", "area"),
    ],
}

metric_info["publish_bytes_received_rate"] = {
    "title": _("PUBLISH messages: Bytes received"),
    "unit": "bytes/s",
    "color": "#00e060",
}

metric_info["publish_bytes_sent_rate"] = {
    "title": _("PUBLISH messages: Bytes sent"),
    "unit": "bytes/s",
    "color": "#0080e0",
}

graph_info["publish_bytes_transmitted"] = {
    "title": _("PUBLISH messages: Bytes sent/received"),
    "metrics": [
        ("publish_bytes_sent_rate", "-area"),
        ("publish_bytes_received_rate", "area"),
    ],
}

metric_info["publish_messages_received_rate"] = {
    "title": _("PUBLISH messages received"),
    "unit": "1/s",
    "color": "#00ffc0",
}

metric_info["publish_messages_sent_rate"] = {
    "title": _("PUBLISH messages sent"),
    "unit": "1/s",
    "color": "#00c0ff",
}

graph_info["publish_messages_transmitted"] = {
    "title": _("PUBLISH messages sent/received"),
    "metrics": [
        ("publish_messages_sent_rate", "-area"),
        ("publish_messages_received_rate", "area"),
    ],
}

metric_info["retained_messages"] = {
    "title": _("Retained messages"),
    "unit": "count",
    "color": "11/a",
}

metric_info["stored_messages"] = {
    "title": _("Stored messages"),
    "unit": "count",
    "color": "14/a",
}

metric_info["stored_messages_bytes"] = {
    "title": _("Size of stored messages"),
    "unit": "bytes",
    "color": "23/a",
}
