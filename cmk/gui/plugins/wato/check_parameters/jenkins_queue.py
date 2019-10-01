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
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_jenkins_queue():
    return Dictionary(elements=[
        ("queue_length",
         Tuple(
             title=_("Upper level for queue length"),
             elements=[
                 Integer(title=_("Warning at"), unit="Tasks"),
                 Integer(title=_("Critical at"), unit="Tasks"),
             ],
         )),
        ('in_queue_since',
         Tuple(
             title=_("Task in queue since"),
             elements=[
                 Age(title=_("Warning at"), default_value=3600),
                 Age(title=_("Critical at"), default_value=7200),
             ],
         )),
        ("stuck", MonitoringState(
            title=_("Task state: Stuck"),
            default_value=2,
        )),
        ("jenkins_stuck_tasks",
         Tuple(
             title=_("Upper level for stuck tasks"),
             elements=[
                 Integer(title=_("Warning at"), unit="Tasks", default_value=1),
                 Integer(title=_("Critical at"), unit="Tasks", default_value=2),
             ],
         )),
        ("blocked", MonitoringState(
            title=_("Task state: Blocked"),
            default_value=0,
        )),
        ("jenkins_blocked_tasks",
         Tuple(
             title=_("Upper level for blocked tasks"),
             elements=[
                 Integer(title=_("Warning at"), unit="Tasks"),
                 Integer(title=_("Critical at"), unit="Tasks"),
             ],
         )),
        ("pending", MonitoringState(title=_("Task state: Pending"), default_value=0)),
        ("jenkins_pending_tasks",
         Tuple(
             title=_("Upper level for pending tasks"),
             elements=[
                 Integer(title=_("Warning at or above"), unit="Tasks"),
                 Integer(title=_("Critical at or above"), unit="Tasks"),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="jenkins_queue",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jenkins_queue,
        title=lambda: _("Jenkins queue"),
    ))
