#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary


def _parameter_valuespec_db_usage():
    return Dictionary(
        elements=[
            (
                "levels",
                Levels(
                    title=_("DB usage"),
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="db_usage",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_db_usage,
        title=lambda: _("DB usage"),
    )
)
