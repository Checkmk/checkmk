#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, Float, Percentage, Tuple


def _parameter_valuespec_psu_wattage() -> Dictionary:
    return Dictionary(
        title=_("Levels for Power Supply Wattage"),
        elements=[
            (
                "levels_abs_upper",
                Tuple(
                    title=_("Upper levels (absolute)"),
                    elements=[
                        Float(title=_("Warning at"), unit="W"),
                        Float(title=_("Critical at"), unit="W"),
                    ],
                ),
            ),
            (
                "levels_abs_lower",
                Tuple(
                    title=_("Lower levels (absolute)"),
                    elements=[
                        Float(title=_("Warning below"), unit="W"),
                        Float(title=_("Critical below"), unit="W"),
                    ],
                ),
            ),
            (
                "levels_perc_upper",
                Tuple(
                    title=_("Upper levels (in percent)"),
                    elements=[
                        Percentage(
                            label=_("Warning at"),
                            default_value=80.0,
                            display_format="%.3f",
                        ),
                        Percentage(
                            label=_("Critical at"),
                            default_value=90.0,
                            display_format="%.3f",
                        ),
                    ],
                ),
            ),
            (
                "levels_perc_lower",
                Tuple(
                    title=_("Lower levels (in percent)"),
                    elements=[
                        Percentage(
                            label=_("Warning below"),
                            default_value=1.0,
                            display_format="%.3f",
                        ),
                        Percentage(
                            label=_("Critical below"),
                            default_value=0.1,
                            display_format="%.3f",
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="psu_wattage",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_psu_wattage,
        title=lambda: _("Power Supply Wattage"),
    )
)
