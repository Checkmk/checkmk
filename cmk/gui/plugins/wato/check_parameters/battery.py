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
from cmk.gui.valuespec import Dictionary, Percentage, TextInput, Tuple


def _item_spec_battery():
    return TextInput(
        title=_("Sensor name"),
        help=_("The identifier of the sensor."),
    )


def _parameter_valuespec_battery() -> Dictionary:
    return Dictionary(
        help=_("This Ruleset sets the threshold limits for battery sensors"),
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Upper levels"),
                    elements=[
                        Percentage(title=_("Warning at")),
                        Percentage(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "levels_lower",
                Tuple(
                    title=_("Lower levels"),
                    elements=[
                        Percentage(title=_("Warning below")),
                        Percentage(title=_("Critical below")),
                    ],
                ),
            ),
        ],
        ignored_keys=["_item_key"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="battery",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_battery,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_battery,
        title=lambda: _("Battery Levels"),
    )
)
