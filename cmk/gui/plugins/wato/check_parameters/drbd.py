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
    Alternative,
    Dictionary,
    DropdownChoice,
    FixedValue,
    ListOf,
    MonitoringState,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def _parameter_valuespec_drbd():
    return Dictionary(elements=[
        ("roles",
         Alternative(
             title=_("Roles"),
             elements=[
                 FixedValue(None, totext="", title=_("Do not monitor")),
                 ListOf(Tuple(orientation="horizontal",
                              elements=[
                                  DropdownChoice(
                                      title=_("DRBD shows up as"),
                                      default_value="running",
                                      choices=[("primary_secondary", _("Primary / Secondary")),
                                               ("primary_primary", _("Primary / Primary")),
                                               ("secondary_primary", _("Secondary / Primary")),
                                               ("secondary_secondary", _("Secondary / Secondary"))],
                                  ),
                                  MonitoringState(title=_("Resulting state"),),
                              ],
                              default_value=("ignore", 0)),
                        title=_("Set roles"),
                        add_label=_("Add role rule"))
             ],
         )),
        (
            "diskstates",
            Alternative(
                title=_("Diskstates"),
                elements=[
                    FixedValue(None, totext="", title=_("Do not monitor")),
                    ListOf(Tuple(
                        elements=[
                            DropdownChoice(
                                title=_("Diskstate"),
                                choices=[
                                    ("primary_Diskless", _("Primary - Diskless")),
                                    ("primary_Attaching", _("Primary - Attaching")),
                                    ("primary_Failed", _("Primary - Failed")),
                                    ("primary_Negotiating", _("Primary - Negotiating")),
                                    ("primary_Inconsistent", _("Primary - Inconsistent")),
                                    ("primary_Outdated", _("Primary - Outdated")),
                                    ("primary_DUnknown", _("Primary - DUnknown")),
                                    ("primary_Consistent", _("Primary - Consistent")),
                                    ("primary_UpToDate", _("Primary - UpToDate")),
                                    ("secondary_Diskless", _("Secondary - Diskless")),
                                    ("secondary_Attaching", _("Secondary - Attaching")),
                                    ("secondary_Failed", _("Secondary - Failed")),
                                    ("secondary_Negotiating", _("Secondary - Negotiating")),
                                    ("secondary_Inconsistent", _("Secondary - Inconsistent")),
                                    ("secondary_Outdated", _("Secondary - Outdated")),
                                    ("secondary_DUnknown", _("Secondary - DUnknown")),
                                    ("secondary_Consistent", _("Secondary - Consistent")),
                                    ("secondary_UpToDate", _("Secondary - UpToDate")),
                                ],
                            ),
                            MonitoringState(title=_("Resulting state"))
                        ],
                        orientation="horizontal",
                    ),
                           title=_("Set diskstates"),
                           add_label=_("Add diskstate rule"))
                ],
            ),
        )
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="drbd",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextAscii(title=_("DRBD device")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_drbd,
        title=lambda: _("DR:BD roles and diskstates"),
    ))
