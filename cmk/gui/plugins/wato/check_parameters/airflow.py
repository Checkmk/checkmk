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
from cmk.gui.valuespec import Dictionary, Float, Tuple


def _parameter_valuespec_airflow():
    return Dictionary(
        elements=[
            (
                "level_low",
                Tuple(
                    title=_("Lower levels"),
                    elements=[
                        Float(
                            title=_("Warning if below"),
                            unit=_("l/s"),
                            default_value=5.0,
                            allow_int=True,
                        ),
                        Float(
                            title=_("Critical if below"),
                            unit=_("l/s"),
                            default_value=2.0,
                            allow_int=True,
                        ),
                    ],
                ),
            ),
            (
                "level_high",
                Tuple(
                    title=_("Upper levels"),
                    elements=[
                        Float(
                            title=_("Warning at"), unit=_("l/s"), default_value=10.0, allow_int=True
                        ),
                        Float(
                            title=_("Critical at"),
                            unit=_("l/s"),
                            default_value=11.0,
                            allow_int=True,
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="airflow",
        group=RulespecGroupCheckParametersEnvironment,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_airflow,
        title=lambda: _("Airflow levels"),
    )
)
