#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _parameter_valuespec_oracle_logswitches() -> Dictionary:
    return Dictionary(
        help=_(
            "This check monitors the number of log switches of an Oracle "
            "database instance in the last 60 minutes. You can set levels "
            "for upper and lower bounds."
        ),
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Set upper levels"),
                    elements=[
                        Integer(
                            title=_("Warning at or above"),
                            unit=_("log switches / hour"),
                            default_value=50,
                        ),
                        Integer(
                            title=_("Critical at or above"),
                            unit=_("log switches / hour"),
                            default_value=100,
                        ),
                    ],
                ),
            ),
            (
                "levels_lower",
                Tuple(
                    title=_("Set lower levels"),
                    elements=[
                        Integer(
                            title=_("Warning at or below"),
                            unit=_("log switches / hour"),
                            default_value=-1,
                        ),
                        Integer(
                            title=_("Critical at or below"),
                            unit=_("log switches / hour"),
                            default_value=-1,
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="oracle_logswitches",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Database SID"), size=12, allow_empty=False),
        parameter_valuespec=_parameter_valuespec_oracle_logswitches,
        title=lambda: _("Oracle Logswitches"),
    )
)
