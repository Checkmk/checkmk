#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Integer,
    TextAscii,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersEnvironment,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


def _parameter_valuespec_hw_temperature():
    return Tuple(help=_("Temperature levels for hardware devices like "
                        "Brocade switches with (potentially) several "
                        "temperature sensors. Sensor IDs can be selected "
                        "in the rule."),
                 elements=[
                     Integer(title=_("warning at"), unit=u"°C", default_value=35),
                     Integer(title=_("critical at"), unit=u"°C", default_value=40),
                 ])


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="hw_temperature",
        group=RulespecGroupCheckParametersEnvironment,
        is_deprecated=True,
        item_spec=lambda: TextAscii(title=_("Sensor ID"),
                                    help=_("The identifier of the thermal sensor.")),
        parameter_valuespec=_parameter_valuespec_hw_temperature,
        title=lambda: _("Hardware temperature, multiple sensors"),
    ))
