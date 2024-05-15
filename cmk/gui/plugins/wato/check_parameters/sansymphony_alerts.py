#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, Migrate, Tuple


def _parameter_valuespec_sansymphony_alerts():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "levels",
                    Tuple(
                        title=_("Number of unacknowlegded alerts"),
                        elements=[
                            Integer(
                                title=_("Warning at"),
                                unit=_("alerts"),
                                default_value=1,
                            ),
                            Integer(
                                title=_("Critical at"),
                                unit=_("alerts"),
                                default_value=2,
                            ),
                        ],
                    ),
                ),
            ],
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"levels": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="sansymphony_alerts",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_sansymphony_alerts,
        title=lambda: _("Sansymphony unacknowlegded alerts"),
    )
)
