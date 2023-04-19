#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Age, Dictionary, TextInput

THIRTY_DAYS = 30 * 24 * 60 * 60
SEVEN_DAYS = 7 * 24 * 60 * 60


def _parameter_valuespec_credentials_expiration() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "expiration_time",
                SimpleLevels(
                    Age,
                    title=_("Time until credentials expiration"),
                    default_value=(THIRTY_DAYS, SEVEN_DAYS),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="credentials_expiration",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("Credentials"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_credentials_expiration,
        title=lambda: _("Credentials Expiration"),
    )
)
