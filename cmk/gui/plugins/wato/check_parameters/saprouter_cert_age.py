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


def _parameter_valuespec_saprouter_cert_age():
    return Dictionary(
        elements=[
            (
                "validity_age",
                Tuple(
                    title=_("Lower levels for certificate age"),
                    elements=[
                        Age(title=_("Warning below"), default_value=30 * 86400),
                        Age(title=_("Critical below"), default_value=7 * 86400),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="saprouter_cert_age",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_saprouter_cert_age,
        title=lambda: _("SAP router certificate time settings"),
    )
)
