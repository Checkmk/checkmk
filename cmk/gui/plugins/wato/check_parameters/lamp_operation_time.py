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
from cmk.gui.valuespec import Age, Dictionary, Migrate, Tuple


def _parameter_valuespec_lamp_operation_time():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "levels",
                    Tuple(
                        elements=[
                            Age(
                                title=_("Warning at"),
                                default_value=1000 * 3600,
                                display=["hours"],
                            ),
                            Age(
                                title=_("Critical at"),
                                default_value=1500 * 3600,
                                display=["hours"],
                            ),
                        ],
                    ),
                ),
            ],
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"levels": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="lamp_operation_time",
        group=RulespecGroupCheckParametersEnvironment,
        parameter_valuespec=_parameter_valuespec_lamp_operation_time,
        title=lambda: _("Beamer lamp operation time"),
    )
)
