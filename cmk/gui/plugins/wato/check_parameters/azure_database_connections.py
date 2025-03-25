#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    TextInput,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Integer


def _parameter_valuespec_connections():
    return Dictionary(
        title=_("Levels connections"),
        elements=[
            (
                "active_connections_lower",
                SimpleLevels(Integer, title=_("Lower levels for active connections")),
            ),
            (
                "active_connections",
                SimpleLevels(Integer, title=_("Upper levels for active connections")),
            ),
            (
                "failed_connections",
                SimpleLevels(Integer, title=_("Failed connections")),
            ),
        ],
        required_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="database_connections",
        item_spec=lambda: TextInput(title=_("Database")),
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_connections,
        title=lambda: _("Azure database connections"),
    )
)
