#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Age, Dictionary


def _parameter_valuespec_mail_latency() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "levels",
                SimpleLevels(
                    spec=Age,
                    default_levels=(40, 60),
                    title=_("Upper levels for mail latency"),
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="mail_latency",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_mail_latency,
        title=lambda: _("Mail latency"),
    )
)
