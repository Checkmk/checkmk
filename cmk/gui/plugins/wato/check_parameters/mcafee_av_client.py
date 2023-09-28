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
from cmk.gui.valuespec import Age, Dictionary, Tuple


def _parameter_valuespec_mcafee_av_client() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "signature_age",
                Tuple(
                    title=_("Time Settings for Signature"),
                    elements=[
                        Age(title=_("Warning at"), default_value=86400),
                        Age(title=_("Critical at"), default_value=7 * 86400),
                    ],
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="mcafee_av_client",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_mcafee_av_client,
        title=lambda: _("McAfee Anti-Virus Time Settings"),
    )
)
