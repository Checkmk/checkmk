#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Integer, Migrate


def _parameter_valuespec_blank_tapes():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "levels_lower",
                    SimpleLevels(
                        spec=Integer,
                        default_levels=(5, 1),
                        direction="lower",
                    ),
                )
            ],
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"levels_lower": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="blank_tapes",
        group=RulespecGroupCheckParametersStorage,
        parameter_valuespec=_parameter_valuespec_blank_tapes,
        title=lambda: _("DIVA CSM: remaining blank tapes"),
    )
)
