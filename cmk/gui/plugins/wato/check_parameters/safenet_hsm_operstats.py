#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Float, Integer, Tuple


def _parameter_valuespec_safenet_hsm_operstats():
    return Dictionary(
        elements=[
            (
                "error_rate",
                Tuple(
                    title=_("Error rate"),
                    elements=[
                        Float(title=_("Warning at"), default_value=0.01, unit=_("1/s")),
                        Float(title=_("Critical at"), default_value=0.05, unit=_("1/s")),
                    ],
                ),
            ),
            (
                "request_rate",
                Levels(
                    title=_("Request rate"),
                    unit=_("1/s"),
                    default_value=None,
                ),
            ),
            (
                "operation_errors",
                Tuple(
                    title=_("Operation errors"),
                    help=_("Sets levels on total operation errors since last counter reset."),
                    elements=[
                        Integer(title=_("Warning at"), default_value=0),
                        Integer(title=_("Critical at"), default_value=1),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="safenet_hsm_operstats",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_safenet_hsm_operstats,
        title=lambda: _("Safenet HSM Operation Stats"),
    )
)
