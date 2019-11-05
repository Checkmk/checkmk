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
    MonitoringState,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_graylog_license():
    return Dictionary(elements=[
        ("expired", MonitoringState(title=_("State when license is expired"), default_value=2)),
        ("violated",
         MonitoringState(title=_("State when license state is violated"), default_value=1)),
        ("valid", MonitoringState(title=_("State when license is not valid"), default_value=2)),
        ("traffic_exceeded",
         MonitoringState(title=_("State when license traffic is exceeded"), default_value=1)),
        ("cluster_not_covered",
         MonitoringState(title=_("State when license does not cover cluster"), default_value=1)),
        ("nodes_exceeded",
         MonitoringState(title=_("State when license nodes exceeded"), default_value=1)),
        ("remote_checks_failed",
         MonitoringState(title=_("State when license remote check failed"), default_value=1)),
        ("expiration",
         Tuple(
             title=_("Time until license expiration"),
             help=_("Remaining days until the Graylog license expires"),
             elements=[
                 Age(title=_("Warning at"), default_value=14 * 24 * 60 * 60),
                 Age(title=_("Critical at"), default_value=7 * 24 * 60 * 60)
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="graylog_license",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_graylog_license,
        title=lambda: _("Graylog license"),
    ))
