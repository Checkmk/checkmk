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
    MonitoringState,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
)


def _parameter_valuespec_threepar_remotecopy():
    return Dictionary(elements=[
        ("1", MonitoringState(
            title=_("Status: NORMAL"),
            default_value=0,
        )),
        ("2", MonitoringState(
            title=_("Status: STARTUP"),
            default_value=1,
        )),
        ("3", MonitoringState(
            title=_("Status: SHUTDOWN"),
            default_value=1,
        )),
        ("4", MonitoringState(
            title=_("Status: ENABLE"),
            default_value=0,
        )),
        ("5", MonitoringState(
            title=_("Status: DISBALE"),
            default_value=2,
        )),
        ("6", MonitoringState(
            title=_("Status: INVALID"),
            default_value=2,
        )),
        ("7", MonitoringState(
            title=_("Status: NODEUP"),
            default_value=1,
        )),
        ("8", MonitoringState(
            title=_("Status: UPGRADE"),
            default_value=0,
        )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="threepar_remotecopy",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_threepar_remotecopy,
        title=lambda: _("3PAR Remote Copy"),
    ))
