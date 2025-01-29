#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, Float, TextInput, Tuple


def _item_spec_hp_msa_psu_voltage():
    return TextInput(title=_("Power supply name"), help=_("The identifier of the power supply."))


def _parameter_valuespec_hp_msa_psu_voltage():
    return Dictionary(
        help=_("Here you can configure the 3.3V and 12V voltage levels for each power supply."),
        elements=[
            (
                "levels_33v_lower",
                Tuple(
                    title=_("3.3 Volt output lower levels"),
                    elements=[
                        Float(title=_("warning if below or equal"), unit="V", default_value=3.25),
                        Float(title=_("critical if below or equal"), unit="V", default_value=3.20),
                    ],
                ),
            ),
            (
                "levels_33v_upper",
                Tuple(
                    title=_("3.3 Volt output upper levels"),
                    elements=[
                        Float(title=_("warning if above or equal"), unit="V", default_value=3.4),
                        Float(title=_("critical if above or equal"), unit="V", default_value=3.45),
                    ],
                ),
            ),
            (
                "levels_5v_lower",
                Tuple(
                    title=_("5 Volt output lower levels"),
                    elements=[
                        Float(title=_("warning if below or equal"), unit="V", default_value=3.25),
                        Float(title=_("critical if below or equal"), unit="V", default_value=3.20),
                    ],
                ),
            ),
            (
                "levels_5v_upper",
                Tuple(
                    title=_("5 Volt output upper levels"),
                    elements=[
                        Float(title=_("warning if above or equal"), unit="V", default_value=3.4),
                        Float(title=_("critical if above or equal"), unit="V", default_value=3.45),
                    ],
                ),
            ),
            (
                "levels_12v_lower",
                Tuple(
                    title=_("12 Volt output lower levels"),
                    elements=[
                        Float(title=_("warning if below or equal"), unit="V", default_value=11.9),
                        Float(title=_("critical if below or equal"), unit="V", default_value=11.8),
                    ],
                ),
            ),
            (
                "levels_12v_upper",
                Tuple(
                    title=_("12 Volt output upper levels"),
                    elements=[
                        Float(title=_("warning if above or equal"), unit="V", default_value=12.1),
                        Float(title=_("critical if above or equal"), unit="V", default_value=12.2),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="hp_msa_psu_voltage",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_hp_msa_psu_voltage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_hp_msa_psu_voltage,
        title=lambda: _("HP MSA power supply voltage levels"),
    )
)
