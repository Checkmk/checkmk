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
from cmk.gui.valuespec import Dictionary, Integer, Percentage, TextInput, Tuple


def _parameter_valuespec_apc_ats_output():
    return Dictionary(
        title=_("Levels for ATS Output parameters"),
        optional_keys=True,
        elements=[
            (
                "output_voltage_max",
                Tuple(
                    title=_("Maximum Levels for Voltage"),
                    elements=[
                        Integer(title=_("Warning at"), unit="Volt"),
                        Integer(title=_("Critical at"), unit="Volt"),
                    ],
                ),
            ),
            (
                "output_voltage_min",
                Tuple(
                    title=_("Minimum Levels for Voltage"),
                    elements=[
                        Integer(title=_("Warning if below"), unit="Volt"),
                        Integer(title=_("Critical if below"), unit="Volt"),
                    ],
                ),
            ),
            (
                "load_perc_max",
                Tuple(
                    title=_("Maximum Levels for load in percent"),
                    elements=[
                        Percentage(title=_("Warning at")),
                        Percentage(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "load_perc_min",
                Tuple(
                    title=_("Minimum Levels for load in percent"),
                    elements=[
                        Percentage(title=_("Warning if below")),
                        Percentage(title=_("Critical if below")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="apc_ats_output",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=lambda: TextInput(
            title=_("ID of phase"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_apc_ats_output,
        title=lambda: _("APC Automatic Transfer Switch Output"),
    )
)
