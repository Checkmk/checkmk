#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_mobileiron_compliance():
    return Dictionary(
        title=_("Mobileiron compliance parameters"),
        elements=[
            (
                "policy_violation_levels",
                Tuple(
                    title=_("Policy violation levels"),
                    elements=[
                        Integer(title=_("Warning at"), default_value=2),
                        Integer(title=_("Critical at"), default_value=3),
                    ],
                ),
            )
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        title=lambda: _("Mobileiron Device"),
        check_group_name="mobileiron_compliance",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mobileiron_compliance,
    )
)
