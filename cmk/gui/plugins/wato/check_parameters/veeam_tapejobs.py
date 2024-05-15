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
from cmk.gui.valuespec import Age, Dictionary, Migrate, TextInput, Tuple


def _parameter_valuespec_veeam_tapejobs():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "levels_upper",
                    Tuple(
                        title=_("Levels for duration of backup job"),
                        elements=[
                            Age(title="Warning at"),
                            Age(title="Critical at"),
                        ],
                    ),
                ),
            ],
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"levels_upper": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="veeam_tapejobs",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(
            title=_("Name of the tape job"),
        ),
        parameter_valuespec=_parameter_valuespec_veeam_tapejobs,
        title=lambda: _("VEEAM tape backup jobs"),
    )
)
