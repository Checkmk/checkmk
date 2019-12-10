#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
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


def _parameter_valuespec_graylog_sidecars():
    return Dictionary(elements=[
        ("active_state",
         MonitoringState(title=_("State when active state is not OK"), default_value=2)),
        ("last_seen",
         Tuple(
             title=_("Time since the sidecar was last seen by graylog"),
             elements=[Age(title=_("Warning at")),
                       Age(title=_("Critical at"))],
         )),
        ("running_lower",
         Tuple(
             title=_("Total number of collectors in state running lower "
                     "level"),
             elements=[
                 Integer(title=_("Warning if less then"), unit="collectors", default_value=1),
                 Integer(title=_("Critical if less then"), unit="collectors", default_value=0)
             ],
         )),
        ("running_upper",
         Tuple(
             title=_("Total number of collectors in state running upper "
                     "level"),
             elements=[
                 Integer(title=_("Warning at"), unit="collectors"),
                 Integer(title=_("Critical at"), unit="collectors")
             ],
         )),
        ("stopped_lower",
         Tuple(
             title=_("Total number of collectors in state stopped lower "
                     "level"),
             elements=[
                 Integer(title=_("Warning if less then"), unit="collectors"),
                 Integer(title=_("Critical if less then"), unit="collectors")
             ],
         )),
        ("stopped_upper",
         Tuple(
             title=_("Total number of collectors in state stopped upper "
                     "level"),
             elements=[
                 Integer(title=_("Warning at"), unit="collectors", default_value=1),
                 Integer(title=_("Critical at"), unit="collectors", default_value=1)
             ],
         )),
        ("failing_lower",
         Tuple(
             title=_("Total number of collectors in state failing lower "
                     "level"),
             elements=[
                 Integer(title=_("Warning if less then"), unit="collectors"),
                 Integer(title=_("Critical if less then"), unit="collectors")
             ],
         )),
        ("failing_upper",
         Tuple(
             title=_("Total number of collectors in state failing upper "
                     "level"),
             elements=[
                 Integer(title=_("Warning at"), unit="collectors", default_value=1),
                 Integer(title=_("Critical at"), unit="collectors", default_value=1)
             ],
         )),
        ("running",
         MonitoringState(title=_("State when collector is in state running"), default_value=0)),
        ("stopped",
         MonitoringState(title=_("State when collector is in state stopped"), default_value=1)),
        ("failing",
         MonitoringState(title=_("State when collector is in state failing"), default_value=2)),
        ("no_ping",
         MonitoringState(title=_("State when no ping signal from sidecar"), default_value=2)),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="graylog_sidecars",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Sidecar name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_graylog_sidecars,
        title=lambda: _("Graylog sidecars"),
    ))
