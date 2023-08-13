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
from cmk.gui.valuespec import Dictionary, Migrate, Percentage, TextInput, Tuple


def _parameter_valuespec_signal_quality():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "levels_lower",
                    Tuple(
                        elements=[
                            Percentage(title=_("Warning if under"), maxvalue=100),
                            Percentage(title=_("Critical if under"), maxvalue=100),
                        ],
                    ),
                ),
            ],
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"levels_lower": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="signal_quality",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("Network specification"), allow_empty=True),
        parameter_valuespec=_parameter_valuespec_signal_quality,
        title=lambda: _("Signal quality of Wireless device"),
    )
)
