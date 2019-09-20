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
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_graylog_messages():
    return Dictionary(elements=[
        ("messages_upper",
         Tuple(
             title=_("Total message count upper levels"),
             elements=[
                 Integer(title=_("Warning at"), allow_empty=False),
                 Integer(title=_("Critical at"), allow_empty=False),
             ],
         )),
        ("messages_lower",
         Tuple(
             title=_("Total message count lower levels"),
             elements=[
                 Integer(title=_("Warning if below"), allow_empty=False),
                 Integer(title=_("Critical if below"), allow_empty=False),
             ],
         )),
        ("avg",
         Integer(
             title=_("Message averaging"),
             help=_("By activating averaging, Check_MK will compute the average of "
                    "the message count over a given interval. If you define "
                    "alerting levels then these will automatically be applied on the "
                    "averaged value. This helps to mask out short peaks. "),
             unit=_("minutes"),
             minvalue=1,
             default_value=30,
         )),
        ("msg_count_avg_upper",
         Tuple(
             title=_("Average message count upper levels"),
             elements=[
                 Integer(title=_("Warning at"), allow_empty=False),
                 Integer(title=_("Critical at"), allow_empty=False),
             ],
         )),
        ("msg_count_avg_lower",
         Tuple(
             title=_("Average message count lower levels"),
             elements=[
                 Integer(title=_("Warning if below"), allow_empty=False),
                 Integer(title=_("Critical if below"), allow_empty=False),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="graylog_messages",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_graylog_messages,
        title=lambda: _("Graylog messages"),
    ))
