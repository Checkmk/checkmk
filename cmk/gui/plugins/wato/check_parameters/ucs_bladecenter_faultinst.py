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
    DropdownChoice,
    ListChoice,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_ucs_bladecenter_faultinst():
    status_choices = [
        (0, _("Ok")),
        (1, _("Warning")),
        (2, _("Critical")),
        (3, _("Unknown")),
    ]
    return Dictionary(
        elements=[
            ("critical",
             DropdownChoice(
                 title=_("Translation of 'critical'-state to Check_mk"),
                 choices=status_choices,
                 default_value=2,
             )),
            ("major",
             DropdownChoice(
                 title=_("Translation of 'major'-state to Check_mk"),
                 choices=status_choices,
                 default_value=1,
             )),
            ("warning",
             DropdownChoice(
                 title=_("Translation of 'warning'-state to Check_mk"),
                 choices=status_choices,
                 default_value=1,
             )),
            ("minor",
             DropdownChoice(
                 title=_("Translation of 'minor'-state to Check_mk"),
                 choices=status_choices,
                 default_value=1,
             )),
            ("info",
             DropdownChoice(
                 title=_("Translation of 'info'-state to Check_mk"),
                 choices=status_choices,
                 default_value=0,
             )),
            ("condition",
             DropdownChoice(
                 title=_("Translation of 'condition'-state to Check_mk"),
                 choices=status_choices,
                 default_value=0,
             )),
            ("cleared",
             DropdownChoice(
                 title=_("Translation of 'cleared'-state to Check_mk"),
                 choices=status_choices,
                 default_value=0,
             )),
            ("show_only",
             ListChoice(
                 title=_("Show and check only the following states"),
                 choices=[
                     ("critical", _("Critical")),
                     ("major", _("Major")),
                     ("warning", _("Warning")),
                     ("minor", _("Minor")),
                     ("info", _("Info")),
                     ("condition", _("Condition")),
                     ("cleared", _("Cleared")),
                 ],
                 toggle_all=True,
                 default_value=[
                     "critical", "major", "warning", "minor", "info", "condition", "cleared"
                 ],
             )),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ucs_bladecenter_faultinst",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ucs_bladecenter_faultinst,
        title=lambda: _("UCS Bladecenter Fault instances"),
    ))
