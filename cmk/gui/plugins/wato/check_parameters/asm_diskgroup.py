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
    DropdownChoice,
    TextAscii,
)
from cmk.gui.plugins.wato.check_parameters.utils import filesystem_elements
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


def _item_spec_asm_diskgroup():
    return TextAscii(
        title=_("ASM Disk Group"),
        help=_("Specify the name of the ASM Disk Group "),
        allow_empty=False,
    )


def _parameter_valuespec_asm_diskgroup():
    return Dictionary(
        elements=filesystem_elements + [
            ("req_mir_free",
             DropdownChoice(
                 title=_("Handling for required mirror space"),
                 totext="",
                 choices=[
                     (False, _("Do not regard required mirror space as free space")),
                     (True, _("Regard required mirror space as free space")),
                 ],
                 help=_(
                     "ASM calculates the free space depending on free_mb or required mirror "
                     "free space. Enable this option to set the check against required "
                     "mirror free space. This only works for normal or high redundancy Disk Groups."
                 ))),
        ],
        hidden_keys=["flex_levels"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="asm_diskgroup",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_asm_diskgroup,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_asm_diskgroup,
        title=lambda: _("ASM Disk Group (used space and growth)"),
    ))
