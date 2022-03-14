#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    ManualCheckParameterRulespec,
    rulespec_registry,
    RulespecGroupEnforcedServicesNetworking,
)
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    Integer,
    IPv4Address,
    NetworkPort,
    TextInput,
    Tuple,
)


def _item_spec_tcp_connections():
    return TextInput(
        title=_("Connection name"),
        help=_("Specify an arbitrary name of this connection here"),
        allow_empty=False,
    )


def _parameter_valuespec_tcp_connections():
    return Dictionary(
        help=_(
            "This rule allows to monitor the existence of specific TCP connections or "
            "TCP/UDP listeners."
        ),
        elements=[
            (
                "proto",
                DropdownChoice(
                    title=_("Protocol"),
                    choices=[("TCP", _("TCP")), ("UDP", _("UDP"))],
                    default_value="TCP",
                ),
            ),
            (
                "state",
                DropdownChoice(
                    title=_("State"),
                    choices=[
                        ("ESTABLISHED", "ESTABLISHED"),
                        ("LISTENING", "LISTENING"),
                        ("SYN_SENT", "SYN_SENT"),
                        ("SYN_RECV", "SYN_RECV"),
                        ("LAST_ACK", "LAST_ACK"),
                        ("CLOSE_WAIT", "CLOSE_WAIT"),
                        ("TIME_WAIT", "TIME_WAIT"),
                        ("CLOSED", "CLOSED"),
                        ("CLOSING", "CLOSING"),
                        ("FIN_WAIT1", "FIN_WAIT1"),
                        ("FIN_WAIT2", "FIN_WAIT2"),
                        ("BOUND", "BOUND"),
                    ],
                ),
            ),
            ("local_ip", IPv4Address(title=_("Local IP address"))),
            ("local_port", NetworkPort(title=_("Local port number"))),
            ("remote_ip", IPv4Address(title=_("Remote IP address"))),
            ("remote_port", NetworkPort(title=_("Remote port number"))),
            (
                "max_states",
                Tuple(
                    title=_("Maximum number of connections or listeners"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "min_states",
                Tuple(
                    title=_("Minimum number of connections or listeners"),
                    elements=[
                        Integer(title=_("Warning if below")),
                        Integer(title=_("Critical if below")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    ManualCheckParameterRulespec(
        check_group_name="tcp_connections",
        group=RulespecGroupEnforcedServicesNetworking,
        item_spec=_item_spec_tcp_connections,
        parameter_valuespec=_parameter_valuespec_tcp_connections,
        title=lambda: _("Monitor specific TCP/UDP connections and listeners"),
    )
)
