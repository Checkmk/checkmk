#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersPrinters,
)
from cmk.gui.valuespec import Dictionary, Percentage, TextInput, Tuple


def _parameter_valuespec_printer_input():
    return Dictionary(
        elements=[
            (
                "capacity_levels",
                Tuple(
                    title=_("Capacity remaining"),
                    elements=[
                        Percentage(title=_("Warning at"), default_value=0.0),
                        Percentage(title=_("Critical at"), default_value=0.0),
                    ],
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
