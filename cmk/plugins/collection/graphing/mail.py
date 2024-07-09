#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, perfometers, Title

UNIT_BYTES = metrics.Unit(metrics.IECNotation("B"))
UNIT_COUNTER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_mail_queue_active_length = metrics.Metric(
    name="mail_queue_active_length",
    title=Title("Length of active mail queue"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_mail_queue_active_size = metrics.Metric(
    name="mail_queue_active_size",
    title=Title("Size of active mail queue"),
    unit=UNIT_BYTES,
    color=metrics.Color.BLUE,
)
metric_mail_queue_deferred_length = metrics.Metric(
    name="mail_queue_deferred_length",
    title=Title("Length of deferred mail queue"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_mail_queue_deferred_size = metrics.Metric(
    name="mail_queue_deferred_size",
    title=Title("Size of deferred mail queue"),
    unit=UNIT_BYTES,
    color=metrics.Color.GREEN,
)
metric_mail_queue_drop_length = metrics.Metric(
    name="mail_queue_drop_length",
    title=Title("Length of drop mail queue"),
    unit=UNIT_COUNTER,
    color=metrics.Color.BLUE,
)
metric_mail_queue_hold_length = metrics.Metric(
    name="mail_queue_hold_length",
    title=Title("Length of hold mail queue"),
    unit=UNIT_COUNTER,
    color=metrics.Color.GREEN,
)
metric_mail_queue_incoming_length = metrics.Metric(
    name="mail_queue_incoming_length",
    title=Title("Length of incoming mail queue"),
    unit=UNIT_COUNTER,
    color=metrics.Color.PURPLE,
)
metric_mail_queue_postfix_total = metrics.Metric(
    name="mail_queue_postfix_total",
    title=Title("Total length of Postfix queue"),
    unit=UNIT_COUNTER,
    color=metrics.Color.LIGHT_CYAN,
)
metric_mail_queue_z1_messenger = metrics.Metric(
    name="mail_queue_z1_messenger",
    title=Title("Length of Z1 messenger mail queue"),
    unit=UNIT_COUNTER,
    color=metrics.Color.DARK_CYAN,
)

perfometer_mail_queue_active_length_mail_queue_deferred_length = perfometers.Stacked(
    name="mail_queue_length",
    lower=perfometers.Perfometer(
        name="mail_queue_active_length",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(20000),
        ),
        segments=["mail_queue_active_length"],
    ),
    upper=perfometers.Perfometer(
        name="mail_queue_deferred_length",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(20000),
        ),
        segments=["mail_queue_deferred_length"],
    ),
)
perfometer_mail_queue_deferred_length = perfometers.Perfometer(
    name="mail_queue_deferred_length",
    focus_range=perfometers.FocusRange(
        perfometers.Closed(0),
        perfometers.Open(20000),
    ),
    segments=["mail_queue_deferred_length"],
)

graph_amount_of_mails_in_queues = graphs.Graph(
    name="amount_of_mails_in_queues",
    title=Title("Amount of mails in queues"),
    compound_lines=[
        "mail_queue_deferred_length",
        "mail_queue_active_length",
    ],
    conflicting=[
        "mail_queue_postfix_total",
        "mail_queue_z1_messenger",
    ],
)
graph_size_of_mails_in_queues = graphs.Graph(
    name="size_of_mails_in_queues",
    title=Title("Size of mails in queues"),
    compound_lines=[
        "mail_queue_deferred_size",
        "mail_queue_active_size",
    ],
    conflicting=[
        "mail_queue_postfix_total",
        "mail_queue_z1_messenger",
    ],
)
graph_amount_of_mails_in_secondary_queues = graphs.Graph(
    name="amount_of_mails_in_secondary_queues",
    title=Title("Amount of mails in queues"),
    compound_lines=[
        "mail_queue_hold_length",
        "mail_queue_incoming_length",
        "mail_queue_drop_length",
    ],
    conflicting=[
        "mail_queue_postfix_total",
        "mail_queue_z1_messenger",
    ],
)
