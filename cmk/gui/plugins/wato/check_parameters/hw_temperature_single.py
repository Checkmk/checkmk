#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Integer,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersEnvironment,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
)


def _parameter_valuespec_hw_temperature_single():
    return Tuple(help=_("Temperature levels for hardware devices like "
                        "DELL Powerconnect that have just one temperature sensor. "),
                 elements=[
                     Integer(title=_("warning at"), unit=u"°C", default_value=35),
                     Integer(title=_("critical at"), unit=u"°C", default_value=40),
                 ])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="hw_temperature_single",
        group=RulespecGroupCheckParametersEnvironment,
        is_deprecated=True,
        parameter_valuespec=_parameter_valuespec_hw_temperature_single,
        title=lambda: _("Hardware temperature, single sensor"),
    ))
