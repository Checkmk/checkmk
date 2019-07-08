#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    Integer,
    IPv4Address,
    TextAscii,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupManualChecksNetworking,
    rulespec_registry,
    ManualCheckParameterRulespec,
)


@rulespec_registry.register
class ManualCheckParameterTCPConnections(ManualCheckParameterRulespec):
    @property
    def group(self):
        return RulespecGroupManualChecksNetworking

    @property
    def check_group_name(self):
        return "tcp_connections"

    @property
    def title(self):
        return _("Monitor specific TCP/UDP connections and listeners")

    @property
    def parameter_valuespec(self):
        return Dictionary(
            help=_("This rule allows to monitor the existence of specific TCP connections or "
                   "TCP/UDP listeners."),
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
                    DropdownChoice(title=_("State"),
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
                                   ]),
                ),
                ("local_ip", IPv4Address(title=_("Local IP address"))),
                ("local_port", Integer(
                    title=_("Local port number"),
                    minvalue=1,
                    maxvalue=65535,
                )),
                ("remote_ip", IPv4Address(title=_("Remote IP address"))),
                ("remote_port", Integer(
                    title=_("Remote port number"),
                    minvalue=1,
                    maxvalue=65535,
                )),
                ("max_states",
                 Tuple(
                     title=_("Maximum number of connections or listeners"),
                     elements=[
                         Integer(title=_("Warning at")),
                         Integer(title=_("Critical at")),
                     ],
                 )),
                ("min_states",
                 Tuple(
                     title=_("Minimum number of connections or listeners"),
                     elements=[
                         Integer(title=_("Warning if below")),
                         Integer(title=_("Critical if below")),
                     ],
                 )),
            ],
        )

    @property
    def item_spec(self):
        return TextAscii(
            title=_("Connection name"),
            help=_("Specify an arbitrary name of this connection here"),
            allow_empty=False,
        )
