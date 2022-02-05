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
from cmk.gui.valuespec import Age, Dictionary, Tuple


def _parameter_valuespec_kaspersky_av_client():
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
            (
                "fullscan_age",
                Tuple(
                    title=_("Time Settings for Fullscan"),
                    elements=[
                        Age(title=_("Warning at"), default_value=86400),
                        Age(title=_("Critical at"), default_value=7 * 86400),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kaspersky_av_client",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_kaspersky_av_client,
        title=lambda: _("Kaspersky Anti-Virus Time Settings"),
    )
)
