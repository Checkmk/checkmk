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
    Age,
    Dictionary,
    DropdownChoice,
    Integer,
    MonitoringState,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_jenkins_nodes():
    return Dictionary(elements=[
        ("jenkins_offline", MonitoringState(title=_("Node state: Offline"), default_value=2)),
        ("jenkins_mode",
         DropdownChoice(
             title=_("Expected mode state."),
             help=_("Choose between Normal (Utilize this node as much "
                    "as possible) and Exclusive (Only build jobs with label "
                    "restrictions matching this node). The state will "
                    "change to warning state, if the mode differs."),
             choices=[
                 ("NORMAL", _("Normal")),
                 ("EXCLUSIVE", _("Exclusive")),
             ],
             default_value="NORMAL",
         )),
        ('jenkins_numexecutors',
         Tuple(
             title=_("Lower level for number of executors of this node"),
             elements=[
                 Integer(title=_("Warning below")),
                 Integer(title=_("Critical below")),
             ],
         )),
        ('jenkins_busyexecutors',
         Tuple(
             title=_("Upper level for number of busy executors of this node"),
             elements=[
                 Integer(title=_("Warning at")),
                 Integer(title=_("Critical at")),
             ],
         )),
        ('jenkins_idleexecutors',
         Tuple(
             title=_("Upper level for number of idle executors of this node"),
             elements=[
                 Integer(title=_("Warning at")),
                 Integer(title=_("Critical at")),
             ],
         )),
        ('avg_response_time',
         Tuple(
             title=_("Average round-trip response time to this node"),
             elements=[
                 Age(title=_("Warning at")),
                 Age(title=_("Critical at")),
             ],
         )),
        ('jenkins_clock',
         Tuple(
             title=_("Clock difference"),
             elements=[
                 Age(title=_("Warning at")),
                 Age(title=_("Critical at")),
             ],
         )),
        ("jenkins_temp",
         Tuple(
             title=_("Absolute levels for free temp space"),
             elements=[
                 Integer(
                     title=_("Warning if below"),
                     unit=_("MB"),
                     minvalue=0,
                 ),
                 Integer(
                     title=_("Critical if below"),
                     unit=_("MB"),
                     minvalue=0,
                 ),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jenkins_nodes",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Node name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jenkins_nodes,
        title=lambda: _("Jenkins nodes"),
    ))
