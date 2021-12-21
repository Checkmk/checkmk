#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, Float, TextInput, Tuple


def _parameter_valuespec_voltage():
    return Dictionary(
        title=_("Voltage Sensor"),
        optional_keys=True,
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Upper Levels for Voltage"),
                    elements=[
                        Float(title=_("Warning at"), default_value=15.00, unit="V"),
                        Float(title=_("Critical at"), default_value=16.00, unit="V"),
                    ],
                ),
            ),
            (
                "levels_lower",
                Tuple(
                    title=_("Lower Levels for Voltage"),
                    elements=[
                        Float(title=_("Warning below"), default_value=10.00, unit="V"),
                        Float(title=_("Critical below"), default_value=9.00, unit="V"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="voltage",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=lambda: TextInput(
            title=_("Sensor Description and Index"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_voltage,
        title=lambda: _("Voltage Sensor"),
    )
)
