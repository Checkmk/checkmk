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
    Dictionary,
    TextAscii,
    MonitoringState,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_keepalived():
    return Dictionary(elements=[
        ("master", MonitoringState(
            title=_("master"),
            default_value=0,
        )),
        ("unknown", MonitoringState(
            title=_("unknown"),
            default_value=3,
        )),
        ("init", MonitoringState(
            title=_("init"),
            default_value=0,
        )),
        ("backup", MonitoringState(
            title=_("backup"),
            default_value=0,
        )),
        ("fault", MonitoringState(
            title=_("fault"),
            default_value=2,
        )),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="keepalived",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("VRRP Instance"),),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_keepalived,
        title=lambda: _("Keepalived Parameters"),
    ))
