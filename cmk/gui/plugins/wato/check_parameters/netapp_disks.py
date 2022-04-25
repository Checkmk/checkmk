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
    Integer,
    Percentage,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def _parameter_valuespec_netapp_disks():
    return Transform(Dictionary(elements=[
        ("failed_spare_ratio",
         Tuple(
             title=_("Failed to spare ratio"),
             help=_("You can set a limit to the failed to spare disk ratio. "
                    "The ratio is calculated with <i>failed / (failed + spare)</i>."),
             elements=[
                 Percentage(title=_("Warning at or above"), default_value=1.0),
                 Percentage(title=_("Critical at or above"), default_value=50.0),
             ],
         )),
        ("offline_spare_ratio",
         Tuple(
             title=_("Offline to spare ratio"),
             help=_("You can set a limit to the offline to spare disk ratio. "
                    "The ratio is calculated with <i>offline / (offline + spare)</i>."),
             elements=[
                 Percentage(title=_("Warning at or above"), default_value=1.0),
                 Percentage(title=_("Critical at or above"), default_value=50.0),
             ],
         )),
        ("number_of_spare_disks",
         Tuple(
             title=_("Number of spare disks"),
             help=_("You can set a lower limit to the absolute number of spare disks."),
             elements=[
                 Integer(title=_("Warning below"), default_value=2, min_value=0),
                 Integer(title=_("Critical below"), default_value=1, min_value=0),
             ],
         )),
    ],),
                     forth=lambda a: "broken_spare_ratio" in a and
                     {"failed_spare_ratio": a["broken_spare_ratio"]} or a)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="netapp_disks",
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_netapp_disks,
        title=lambda: _("Filer Disk Levels (NetApp, IBM SVC)"),
    ))
