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


def _parameter_valuespec_eaton_enviroment():
    return Dictionary(
        elements=[
            (
                "temp",
                Tuple(
                    title=_("Temperature"),
                    elements=[
                        Integer(title=_("warning at"), unit="°C", default_value=26),
                        Integer(title=_("critical at"), unit="°C", default_value=30),
                    ],
                ),
            ),
            (
                "remote_temp",
                Tuple(
                    title=_("Remote Temperature"),
                    elements=[
                        Integer(title=_("warning at"), unit="°C", default_value=26),
                        Integer(title=_("critical at"), unit="°C", default_value=30),
                    ],
                ),
            ),
            (
                "humidity",
                Tuple(
                    title=_("Humidity"),
                    elements=[
                        Integer(title=_("warning at"), unit="%", default_value=60),
                        Integer(title=_("critical at"), unit="%", default_value=75),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="eaton_enviroment",
        group=RulespecGroupCheckParametersEnvironment,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_eaton_enviroment,
        title=lambda: _("Temperature and Humidity for Eaton UPS"),
    )
)
