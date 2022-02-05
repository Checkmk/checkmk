#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Age, Dictionary, Tuple


def _parameter_valuespec_azure_ad():
    return Dictionary(
        elements=[
            (
                "age",
                Tuple(
                    title=_("Time since last AD Connect sync"),
                    elements=[
                        Age(title=_("Warning at"), default_value=1800),
                        Age(title=_("Critical at"), default_value=3600),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="azure_ad",
        match_type="dict",
        group=RulespecGroupCheckParametersNetworking,
        parameter_valuespec=_parameter_valuespec_azure_ad,
        title=lambda: _("Azure AD Connect"),
    )
)
