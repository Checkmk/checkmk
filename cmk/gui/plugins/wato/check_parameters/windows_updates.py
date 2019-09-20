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
    Checkbox,
    Integer,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_windows_updates():
    return Tuple(
        title=_("Parameters for the Windows Update Check with WSUS"),
        help=_("Set the according numbers to 0 if you want to disable alerting."),
        elements=[
            Integer(title=_("Warning if at least this number of important updates are pending")),
            Integer(title=_("Critical if at least this number of important updates are pending")),
            Integer(title=_("Warning if at least this number of optional updates are pending")),
            Integer(title=_("Critical if at least this number of optional updates are pending")),
            Age(title=_("Warning if time until forced reboot is less then"), default_value=604800),
            Age(title=_("Critical if time time until forced reboot is less then"),
                default_value=172800),
            Checkbox(title=_("display all important updates verbosely"), default_value=True),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="windows_updates",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_windows_updates,
        title=lambda: _("WSUS (Windows Updates)"),
    ))
