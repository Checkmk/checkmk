#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_carbon_monoxide():
    return Dictionary(
        elements=[
            (
                "levels_ppm",
                Tuple(
                    title="Levels in parts per million",
                    elements=[
                        Integer(title=_("Warning at"), unit=_("ppm"), default_value=10),
                        Integer(title=_("Critical at"), unit=_("ppm"), default_value=25),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="carbon_monoxide",
        group=RulespecGroupCheckParametersEnvironment,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_carbon_monoxide,
        title=lambda: _("Carbon monoxide"),
    )
)
