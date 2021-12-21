#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_tcp_conn_stats():
    return Dictionary(
        elements=[
            (
                "ESTABLISHED",
                Tuple(
                    title=_("ESTABLISHED"),
                    help=_("connection up and passing data"),
                    elements=[
                        Integer(title=_("Warning at"), label=_("connections")),
                        Integer(title=_("Critical at"), label=_("connections")),
                    ],
                ),
            ),
            (
                "SYN_SENT",
                Tuple(
                    title=_("SYN_SENT"),
                    help=_(
                        "session has been requested by us; waiting for reply from remote endpoint"
                    ),
                    elements=[
                        Integer(title=_("Warning at"), label=_("connections")),
                        Integer(title=_("Critical at"), label=_("connections")),
                    ],
                ),
            ),
            (
                "SYN_RECV",
                Tuple(
                    title=_("SYN_RECV"),
                    help=_(
                        "session has been requested by a remote endpoint "
                        "for a socket on which we were listening"
                    ),
                    elements=[
                        Integer(title=_("Warning at"), label=_("connections")),
                        Integer(title=_("Critical at"), label=_("connections")),
                    ],
                ),
            ),
            (
                "LAST_ACK",
                Tuple(
                    title=_("LAST_ACK"),
                    help=_(
                        "our socket is closed; remote endpoint has also shut down; "
                        " we are waiting for a final acknowledgement"
                    ),
                    elements=[
                        Integer(title=_("Warning at"), label=_("connections")),
                        Integer(title=_("Critical at"), label=_("connections")),
                    ],
                ),
            ),
            (
                "CLOSE_WAIT",
                Tuple(
                    title=_("CLOSE_WAIT"),
                    help=_(
                        "remote endpoint has shut down; the kernel is waiting "
                        "for the application to close the socket"
                    ),
                    elements=[
                        Integer(title=_("Warning at"), label=_("connections")),
                        Integer(title=_("Critical at"), label=_("connections")),
                    ],
                ),
            ),
            (
                "TIME_WAIT",
                Tuple(
                    title=_("TIME_WAIT"),
                    help=_("socket is waiting after closing for any packets left on the network"),
                    elements=[
                        Integer(title=_("Warning at"), label=_("connections")),
                        Integer(title=_("Critical at"), label=_("connections")),
                    ],
                ),
            ),
            (
                "CLOSED",
                Tuple(
                    title=_("CLOSED"),
                    help=_("socket is not being used"),
                    elements=[
                        Integer(title=_("Warning at"), label=_("connections")),
                        Integer(title=_("Critical at"), label=_("connections")),
                    ],
                ),
            ),
            (
                "CLOSING",
                Tuple(
                    title=_("CLOSING"),
                    help=_(
                        "our socket is shut down; remote endpoint is shut down; "
                        "not all data has been sent"
                    ),
                    elements=[
                        Integer(title=_("Warning at"), label=_("connections")),
                        Integer(title=_("Critical at"), label=_("connections")),
                    ],
                ),
            ),
            (
                "FIN_WAIT1",
                Tuple(
                    title=_("FIN_WAIT1"),
                    help=_(
                        "our socket has closed; we are in the process of "
                        "tearing down the connection"
                    ),
                    elements=[
                        Integer(title=_("Warning at"), label=_("connections")),
                        Integer(title=_("Critical at"), label=_("connections")),
                    ],
                ),
            ),
            (
                "FIN_WAIT2",
                Tuple(
                    title=_("FIN_WAIT2"),
                    help=_(
                        "the connection has been closed; our socket is waiting "
                        "for the remote endpoint to shutdown"
                    ),
                    elements=[
                        Integer(title=_("Warning at"), label=_("connections")),
                        Integer(title=_("Critical at"), label=_("connections")),
                    ],
                ),
            ),
            (
                "LISTEN",
                Tuple(
                    title=_("LISTEN"),
                    help=_(
                        "represents waiting for a connection request from any remote TCP and port"
                    ),
                    elements=[
                        Integer(title=_("Warning at"), label=_("connections")),
                        Integer(title=_("Critical at"), label=_("connections")),
                    ],
                ),
            ),
            (
                "BOUND",
                Tuple(
                    title=_("BOUND"),
                    help=_(
                        "the socket has been created and an address assigned "
                        "to with bind(). The TCP stack is not active yet. "
                        "This state is only reported on Solaris."
                    ),
                    elements=[
                        Integer(title=_("Warning at"), label=_("connections")),
                        Integer(title=_("Critical at"), label=_("connections")),
                    ],
                ),
            ),
            (
                "IDLE",
                Tuple(
                    title=_("IDLE"),
                    help=_(
                        "a TCP session that is active but that has no data being "
                        "transmitted by either device for a prolonged period of time"
                    ),
                    elements=[
                        Integer(title=_("Warning at"), label=_("connections")),
                        Integer(title=_("Critical at"), label=_("connections")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="tcp_conn_stats",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_tcp_conn_stats,
        title=lambda: _("TCP connection statistics"),
    )
)
