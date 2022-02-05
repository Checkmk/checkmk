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
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _item_spec_power_multiitem():
    return TextInput(
        title=_("Component"),
        help=_("The identifier of device component the consumed power is related to."),
    )


def _parameter_valuespec_power_multiitem():
    return Dictionary(
        elements=[
            (
                "power_upper_levels",
                Tuple(
                    title=_("Alert on too high power consumption"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("W"), default_value=90),
                        Integer(title=_("Critical at"), unit=_("W"), default_value=100),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="power_multiitem",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_power_multiitem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_power_multiitem,
        title=lambda: _("Device Component Power Consumption"),
    )
)
