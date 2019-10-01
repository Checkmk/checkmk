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
    Integer,
    Float,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_skype_sip():
    return Dictionary(elements=[
        ('message_processing_time',
         Dictionary(
             title=_("Average Incoming Message Processing Time"),
             elements=[
                 ("upper",
                  Tuple(elements=[
                      Float(title=_("Warning at"), unit=_("seconds"), default_value=1.0),
                      Float(title=_("Critical at"), unit=_("seconds"), default_value=2.0),
                  ],)),
             ],
             optional_keys=[],
         )),
        ('incoming_responses_dropped',
         Dictionary(
             title=_("Incoming Responses Dropped"),
             elements=[
                 ("upper",
                  Tuple(elements=[
                      Float(title=_("Warning at"), unit=_("per second"), default_value=1.0),
                      Float(title=_("Critical at"), unit=_("per second"), default_value=2.0),
                  ],)),
             ],
             optional_keys=[],
         )),
        ('incoming_requests_dropped',
         Dictionary(
             title=_("Incoming Requests Dropped"),
             elements=[
                 ("upper",
                  Tuple(elements=[
                      Float(title=_("Warning at"), unit=_("per second"), default_value=1.0),
                      Float(title=_("Critical at"), unit=_("per second"), default_value=2.0),
                  ],)),
             ],
             optional_keys=[],
         )),
        ('queue_latency',
         Dictionary(
             title=_("Queue Latency"),
             elements=[
                 ("upper",
                  Tuple(elements=[
                      Float(title=_("Warning at"), unit=_("seconds"), default_value=0.1),
                      Float(title=_("Critical at"), unit=_("seconds"), default_value=0.2),
                  ],)),
             ],
             optional_keys=[],
         )),
        ('sproc_latency',
         Dictionary(
             title=_("Sproc Latency"),
             elements=[
                 ("upper",
                  Tuple(elements=[
                      Float(title=_("Warning at"), unit=_("seconds"), default_value=0.1),
                      Float(title=_("Critical at"), unit=_("seconds"), default_value=0.2),
                  ],)),
             ],
             optional_keys=[],
         )),
        ('throttled_requests',
         Dictionary(
             title=_("Throttled requests"),
             elements=[
                 ("upper",
                  Tuple(elements=[
                      Float(title=_("Warning at"), unit=_("per second"), default_value=0.2),
                      Float(title=_("Critical at"), unit=_("per second"), default_value=0.4),
                  ],)),
             ],
             optional_keys=[],
         )),
        ('local_503_responses',
         Dictionary(
             title=_("Local HTTP 503 Responses"),
             elements=[
                 ("upper",
                  Tuple(elements=[
                      Float(title=_("Warning at"), unit=_("per second"), default_value=1.0),
                      Float(title=_("Critical at"), unit=_("per second"), default_value=2.0),
                  ],)),
             ],
             optional_keys=[],
         )),
        ('timedout_incoming_messages',
         Dictionary(
             title=_("Incoming Messages Timed out"),
             elements=[
                 ("upper",
                  Tuple(elements=[
                      Integer(title=_("Warning at"), default_value=2),
                      Integer(title=_("Critical at"), default_value=4),
                  ],)),
             ],
             optional_keys=[],
         )),
        ('holding_time_incoming',
         Dictionary(
             title=_("Average Holding Time For Incoming Messages"),
             elements=[
                 ("upper",
                  Tuple(elements=[
                      Float(title=_("Warning at"), unit=_("seconds"), default_value=1.0),
                      Float(title=_("Critical at"), unit=_("seconds"), default_value=2.0),
                  ],)),
             ],
             optional_keys=[],
         )),
        ('flow_controlled_connections',
         Dictionary(
             title=_("Flow-controlled Connections"),
             elements=[
                 ("upper",
                  Tuple(elements=[
                      Integer(title=_("Warning at"), default_value=1),
                      Integer(title=_("Critical at"), default_value=2),
                  ],)),
             ],
             optional_keys=[],
         )),
        ('outgoing_queue_delay',
         Dictionary(
             title=_("Average Outgoing Queue Delay"),
             elements=[
                 ("upper",
                  Tuple(elements=[
                      Float(title=_("Warning at"), unit=_("seconds"), default_value=2.0),
                      Float(title=_("Critical at"), unit=_("seconds"), default_value=4.0),
                  ],)),
             ],
             optional_keys=[],
         )),
        ('timedout_sends',
         Dictionary(
             title=_("Sends Timed-Out"),
             elements=[
                 ("upper",
                  Tuple(elements=[
                      Float(title=_("Warning at"), unit=_("per second"), default_value=0.01),
                      Float(title=_("Critical at"), unit=_("per second"), default_value=0.02),
                  ],)),
             ],
             optional_keys=[],
         )),
        ('authentication_errors',
         Dictionary(
             title=_("Authentication System Errors"),
             elements=[
                 ("upper",
                  Tuple(elements=[
                      Float(title=_("Warning at"), unit=_("per second"), default_value=1.0),
                      Float(title=_("Critical at"), unit=_("per second"), default_value=2.0),
                  ],)),
             ],
             optional_keys=[],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="skype_sip",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_skype_sip,
        title=lambda: _("Skype for Business SIP Stack"),
    ))
