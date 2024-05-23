#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, Float, Percentage, TextInput, Tuple, ValueSpec


def _parameter_valuespec_psu_wattage() -> Dictionary:
    return Dictionary(
        title=_("Levels for power supply wattage"),
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
                        ),
                        Percentage(
                            label=_("Critical at"),
                            default_value=90.0,
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
                        ),
                        Percentage(
                            label=_("Critical below"),
                            default_value=0.1,
                        ),
                    ],
                ),
            ),
        ],
    )


def _item_spec() -> ValueSpec:
    return TextInput(title=_("PSU"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="psu_wattage",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_psu_wattage,
        title=lambda: _("Power supply wattage"),
        item_spec=_item_spec,
    )
)
