#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, Float, Migrate, Tuple


def _parameter_valuespec_ps_voltage() -> Migrate:
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "levels_lower",
                    Tuple(
                        elements=[
                            Float(title=_("Warning below"), unit="V"),
                            Float(title=_("Critical below"), unit="V"),
                        ],
                    ),
                ),
                (
                    "levels_upper",
                    Tuple(
                        elements=[
                            Float(title=_("Warning at"), unit="V"),
                            Float(title=_("Critical at"), unit="V"),
                        ],
                    ),
                ),
            ],
            optional_keys=[],
        ),
        migrate=lambda p: (
            p
            if isinstance(p, dict)
            else {"levels_lower": (p[0], p[1]), "levels_upper": (p[2], p[3])}
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ps_voltage",
        group=RulespecGroupCheckParametersEnvironment,
        parameter_valuespec=_parameter_valuespec_ps_voltage,
        title=lambda: _("Output Voltage of Power Supplies"),
    )
)
