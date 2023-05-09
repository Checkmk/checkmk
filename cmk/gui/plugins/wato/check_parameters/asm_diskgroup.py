#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
