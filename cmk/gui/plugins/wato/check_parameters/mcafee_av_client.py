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
from cmk.gui.valuespec import Age, Dictionary, Transform, Tuple


def _transform_mcafee_av_client(params):
    if isinstance(params, dict):
        return params
    return {"signature_age": params}


def _parameter_valuespec_mcafee_av_client():
    return Transform(
        valuespec=Dictionary(
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
        ),
        forth=_transform_mcafee_av_client,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="mcafee_av_client",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_mcafee_av_client,
        title=lambda: _("McAfee Anti-Virus Time Settings"),
    )
)
