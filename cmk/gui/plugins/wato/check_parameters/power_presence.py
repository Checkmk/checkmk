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
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput


def _parameter_valuespec_power_presence():
    return Dictionary(
        elements=[
            (
                "power_off_criticality",
                MonitoringState(
                    title=_("Service criticality"),
                    help=_("Criticality of the service when sensors detect that power is off."),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="power_presence",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=lambda: TextInput(
            title=_("Sensor Name"), help=_("The power supply sensor name as shown in the service")
        ),
        parameter_valuespec=_parameter_valuespec_power_presence,
        title=lambda: _("Power Presence Sensors"),
    )
)
