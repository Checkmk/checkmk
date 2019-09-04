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


@rulespec_registry.register
class RulespecCheckgroupParametersJenkinsNodes(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "jenkins_nodes"

    @property
    def title(self):
        return _("Jenkins nodes")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ("jenkins_offline", MonitoringState(title=_("Node state: Offline"), default_value=2)),
            ('jenkins_numexecutors',
             Tuple(
                 title=_("Lower level for number of executors of this node"),
                 elements=[
                     Integer(title=_("Warning below")),
                     Integer(title=_("Critical below")),
                 ],
             )),
            ('jenkins_response',
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
             Tuple(title=_("Absolute levels for free temp space"),
                   elements=[
                       Integer(title=_("Warning if below"), unit=_("MB"), minvalue=0),
                       Integer(title=_("Critical if below"), unit=_("MB"), minvalue=0),
                   ],
                   allow_empty=False)),
        ],)

    @property
    def item_spec(self):
        return TextAscii(title=_("Node name"))
