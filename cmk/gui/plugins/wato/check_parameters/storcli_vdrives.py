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
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def _item_spec_storcli_vdrives():
    return TextAscii(
        title=_("Virtual Drive"),
        allow_empty=False,
    )


def _parameter_valuespec_storcli_vdrives():
    return Dictionary(
        title=_("Evaluation of VDrive States"),
        elements=[
            ("Optimal", MonitoringState(
                title=_("State for <i>Optimal</i>"),
                default_value=0,
            )),
            ("Partially Degraded",
             MonitoringState(
                 title=_("State for <i>Partially Degraded</i>"),
                 default_value=1,
             )),
            ("Degraded", MonitoringState(
                title=_("State for <i>Degraded</i>"),
                default_value=2,
            )),
            ("Offline", MonitoringState(
                title=_("State for <i>Offline</i>"),
                default_value=1,
            )),
            ("Recovery", MonitoringState(
                title=_("State for <i>Recovery</i>"),
                default_value=1,
            )),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="storcli_vdrives",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_storcli_vdrives,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_storcli_vdrives,
        title=lambda: _("LSI RAID VDrives (StorCLI)"),
    ))
