#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2020             mk@mathias-kettner.de |
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
    MonitoringState,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_3par_remotecopygroup():
    return Dictionary(elements=[
        ("0", MonitoringState(title="Status: INVALID", default_value=2)),
        ("1", MonitoringState(title="Status: NEW", default_value=0)),
        ("2", MonitoringState(title="Status: STARTING", default_value=1)),
        ("3", MonitoringState(title="Status: STARTED", default_value=1)),
        ("4", MonitoringState(title="Status: RESTART", default_value=1)),
        ("5", MonitoringState(title="Status: STOPPED", default_value=2)),
        ("6", MonitoringState(title="Status: BACKUP", default_value=1)),
        ("7", MonitoringState(title="Status: FAILSAFE", default_value=2)),
        ("8", MonitoringState(title="Status: UNKOWN", default_value=3)),
        ("9", MonitoringState(title="Status: LOGGING", default_value=1)),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="gp_threepar_remotecopygroups",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_3par_remotecopygroup,
        title=lambda: _("3PAR Remote Copy Groups"),
    ))
