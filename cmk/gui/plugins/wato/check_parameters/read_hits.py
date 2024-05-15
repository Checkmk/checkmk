#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, Float, Migrate, TextInput, Tuple


def _parameter_valuespec_read_hits() -> Migrate:
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "levels_lower",
                    Tuple(
                        title=_("Prefetch hits"),
                        elements=[
                            Float(title=_("Warning at or below"), default_value=85.0),
                            Float(title=_("Critical at or below"), default_value=70.0),
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
        check_group_name="read_hits",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("Port index or 'Total'")),
        parameter_valuespec=_parameter_valuespec_read_hits,
        title=lambda: _("DDN S2A read prefetch hits"),
    )
)
