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
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_entersekt_soaprrors():
    return Dictionary(
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Upper levels for Soap Service Errors"),
                    elements=[
                        Integer(title=_("Warning if above"), default_value=100),
                        Integer(title=_("Critical if above"), default_value=200),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="entersekt_soaprrors",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_entersekt_soaprrors,
        title=lambda: _("Entersekt Soap Service Errors"),
    )
)
