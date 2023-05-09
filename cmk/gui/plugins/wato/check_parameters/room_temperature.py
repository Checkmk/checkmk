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


def _parameter_valuespec_room_temperature():
    return Tuple(
        help=_("Temperature levels for external thermometers that are used "
               "for monitoring the temperature of a datacenter. An example "
               "is the webthem from W&T."),
        elements=[
            Integer(title=_("warning at"), unit=u"°C", default_value=26),
            Integer(title=_("critical at"), unit=u"°C", default_value=30),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="room_temperature",
        group=RulespecGroupCheckParametersEnvironment,
        is_deprecated=True,
        item_spec=lambda: TextAscii(title=_("Sensor ID"),
                                    help=_("The identifier of the thermal sensor.")),
        parameter_valuespec=_parameter_valuespec_room_temperature,
        title=lambda: _("Room temperature (external thermal sensors)"),
    ))
