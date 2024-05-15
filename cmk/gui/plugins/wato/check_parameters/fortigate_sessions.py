#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Integer, Migrate


def fortigate_sessions_element() -> Migrate:
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "levels",
                    SimpleLevels(
                        spec=Integer,
                        title=_("Levels for active sessions"),
                        default_levels=(100000, 150000),
                    ),
                ),
            ],
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"levels": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="fortigate_sessions",
        group=RulespecGroupCheckParametersNetworking,
        parameter_valuespec=fortigate_sessions_element,
        title=lambda: _("Fortigate Active Sessions"),
    )
)
