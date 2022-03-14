#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import TextInput


def _item_spec_brightness():
    return TextInput(
        title=_("Sensor name"),
        help=_("The identifier of the sensor."),
    )


def _parameter_valuespec_brightness():
    return Levels(
        title=_("Brightness"),
        unit=_("lx"),
        default_value=None,
        default_difference=(2.0, 4.0),
        default_levels=(50.0, 100.0),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="brightness",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_brightness,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_brightness,
        title=lambda: _("Brightness Levels"),
    )
)
