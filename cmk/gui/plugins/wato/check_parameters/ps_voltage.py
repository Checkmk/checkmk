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
from cmk.gui.valuespec import Float, Tuple


def _parameter_valuespec_ps_voltage():
    return Tuple(
        elements=[
            Float(title=_("Warning below"), unit="V"),
            Float(title=_("Critical below"), unit="V"),
            Float(title=_("Warning at or above"), unit="V"),
            Float(title=_("Critical at or above"), unit="V"),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ps_voltage",
        group=RulespecGroupCheckParametersEnvironment,
        parameter_valuespec=_parameter_valuespec_ps_voltage,
        title=lambda: _("Output Voltage of Power Supplies"),
    )
)
