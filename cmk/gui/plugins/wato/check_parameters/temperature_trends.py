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
from cmk.gui.valuespec import Dictionary, Integer, Optional, TextInput, Tuple


def _parameter_valuespec_temperature_trends():
    return Dictionary(
        title=_("Temperature Trend Analysis"),
        help=_(
            "This rule enables and configures a trend analysis and corresponding limits for devices, "
            "which have their own limits configured on the device. It will only work for supported "
            "checks, right now the <tt>adva_fsp_temp</tt> check."
        ),
        elements=[
            (
                "trend_range",
                Optional(
                    valuespec=Integer(
                        title=_("Time range for temperature trend computation"),
                        default_value=30,
                        minvalue=5,
                        unit=_("minutes"),
                    ),
                    title=_("Trend computation"),
                    label=_("Enable trend computation"),
                ),
            ),
            (
                "trend_c",
                Tuple(
                    title=_("Levels on trends in degrees Celsius per time range"),
                    elements=[
                        Integer(title=_("Warning at"), unit="°C / " + _("range"), default_value=5),
                        Integer(
                            title=_("Critical at"), unit="°C / " + _("range"), default_value=10
                        ),
                    ],
                ),
            ),
            (
                "trend_timeleft",
                Tuple(
                    title=_("Levels on the time left until limit is reached"),
                    elements=[
                        Integer(
                            title=_("Warning if below"),
                            unit=_("minutes"),
                            default_value=240,
                        ),
                        Integer(
                            title=_("Critical if below"),
                            unit=_("minutes"),
                            default_value=120,
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="temperature_trends",
        group=RulespecGroupCheckParametersEnvironment,
        is_deprecated=True,
        item_spec=lambda: TextInput(
            title=_("Sensor ID"), help=_("The identifier of the thermal sensor.")
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_temperature_trends,
        title=lambda: _("Temperature trends for devices with builtin levels"),
    )
)
