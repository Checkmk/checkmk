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
from cmk.gui.valuespec import Integer, Tuple


def _parameter_valuespec_single_humidity():
    return Tuple(
        help=_("This Ruleset sets the threshold limits for humidity sensors"),
        elements=[
            Integer(title=_("Critical at or below"), unit="%"),
            Integer(title=_("Warning at or below"), unit="%"),
            Integer(title=_("Warning at or above"), unit="%"),
            Integer(title=_("Critical at or above"), unit="%"),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="single_humidity",
        group=RulespecGroupCheckParametersEnvironment,
        parameter_valuespec=_parameter_valuespec_single_humidity,
        title=lambda: _("Humidity Levels for devices with a single sensor"),
    )
)
