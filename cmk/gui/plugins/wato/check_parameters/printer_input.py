#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersPrinters,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Percentage, TextInput


def _parameter_valuespec_printer_input():
    return Dictionary(
        elements=[
            (
                "capacity_levels",
                SimpleLevels(
                    title=_("Capacity remaining"),
                    spec=Percentage,
                    default_levels=(0.0, 0.0),
                    direction="lower",
                ),
            ),
        ],
        default_keys=["capacity_levels"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="printer_input",
        group=RulespecGroupCheckParametersPrinters,
        item_spec=lambda: TextInput(title=_("Unit Name"), allow_empty=True),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_printer_input,
        title=lambda: _("Printer Input Units"),
    )
)
