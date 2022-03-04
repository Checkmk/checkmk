#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, Percentage, TextInput, Transform, Tuple


def _transform_smoke_detection_params(params):
    if isinstance(params, tuple):
        return {"levels": params}
    return params


def _parameter_valuespec_smoke():
    return Transform(
        valuespec=Dictionary(
            help=_("For devices that measure smoke in percent"),
            elements=[
                (
                    "levels",
                    Tuple(
                        title=_("Upper limits in percent"),
                        elements=[
                            Percentage(title=_("Warning at"), allow_int=True, default_value=1),
                            Percentage(title=_("Critical at"), allow_int=True, default_value=5),
                        ],
                    ),
                ),
            ],
        ),
        forth=_transform_smoke_detection_params,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="smoke",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=lambda: TextInput(title=_("Sensor ID"), help=_("The identifier of the sensor.")),
        parameter_valuespec=_parameter_valuespec_smoke,
        title=lambda: _("Smoke Detection"),
    )
)
