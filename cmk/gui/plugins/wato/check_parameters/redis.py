#!/usr/bin/env python
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Percentage


def _vs_hitratio() -> Dictionary:
    return Dictionary(
        title=_("Parameters for the key hit ratio"),
        elements=[
            (
                "levels_upper_hitratio",
                SimpleLevels(Percentage, title=_("Upper levels for hit ratio")),
            ),
            (
                "levels_lower_hitratio",
                SimpleLevels(Percentage, title=_("Lower levels for hit ratio")),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="redis_hitratio",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_hitratio,
        title=lambda: _("Redis/Hitratio"),
    )
)
