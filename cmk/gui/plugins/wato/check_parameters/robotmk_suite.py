#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Percentage, TextInput


def _parameter_valuespec() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "upper_levels_runtime_percentage",
                SimpleLevels(
                    spec=Percentage,
                    unit="%",
                    default_levels=(80.0, 90.0),
                    title=_("Upper levels on suite runtime relative to overall timeout"),
                    help=_(
                        "The runtime of a suite is limited by the maximum number of attempts "
                        "multiplied by the timeout per attempt. This settings configures "
                        "thresholds on the suite runtime with respect to this overall limit."
                    ),
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="robotmk_suite",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Suite")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec,
        title=lambda: _("Robotmk Suite Status"),
    )
)
