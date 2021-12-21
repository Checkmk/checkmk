#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Float, Tuple


def _parameter_valuespec_mcafee_web_gateway():
    return Dictionary(
        elements=[
            (
                "infections",
                Tuple(
                    title=_("Upper levels for infections"),
                    help=_(
                        "Here you can specify upper levels for the number of "
                        "infections detected by the McAfee Gateway Antimalware Engine."
                    ),
                    elements=[
                        Float(title=_("Warning at")),
                        Float(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "connections_blocked",
                Tuple(
                    title=_("Upper levels for blocked connections"),
                    elements=[
                        Float(title=_("Warning at")),
                        Float(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="mcafee_web_gateway",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mcafee_web_gateway,
        title=lambda: _("McAfee web gateway statistics"),
    )
)
