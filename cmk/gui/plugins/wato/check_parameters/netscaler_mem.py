#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Dictionary, Migrate, Percentage, Tuple


def _parameter_valuespec_netscaler_mem() -> Migrate:
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "levels",
                    Tuple(
                        title=_("Specify levels in percentage of total memory usage"),
                        elements=[
                            Percentage(
                                title=_("Warning at"),
                                default_value=80.0,
                                maxvalue=100.0,
                            ),
                            Percentage(
                                title=_("Critical at"),
                                default_value=90.0,
                                maxvalue=100.0,
                            ),
                        ],
                    ),
                ),
            ],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"levels": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="netscaler_mem",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_netscaler_mem,
        title=lambda: _("Netscaler memory usage"),
    )
)
