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
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)


def _parameter_valuespec_vm_heartbeat():
    return Dictionary(
        optional_keys=False,
        elements=[
            ("heartbeat_missing",
             MonitoringState(
                 title=_("No heartbeat"),
                 help=_("Guest operating system may have stopped responding."),
                 default_value=2,
             )),
            ("heartbeat_intermittend",
             MonitoringState(
                 title=_("Intermittent heartbeat"),
                 help=_("May be due to high guest load."),
                 default_value=1,
             )),
            ("heartbeat_no_tools",
             MonitoringState(
                 title=_("Heartbeat tools missing or not installed"),
                 help=_("No VMWare Tools installed."),
                 default_value=1,
             )),
            ("heartbeat_ok",
             MonitoringState(
                 title=_("Heartbeat OK"),
                 help=_("Guest operating system is responding normally."),
                 default_value=0,
             )),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="vm_heartbeat",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_vm_heartbeat,
        title=lambda: _("Virtual machine (for example ESX) heartbeat status"),
    ))
