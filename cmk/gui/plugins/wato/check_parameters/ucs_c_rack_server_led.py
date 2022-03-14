#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersHardware,
)
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput

COLORS_DEF_STATES = [
    ("amber", 1),
    ("blue", 0),
    ("green", 0),
    ("red", 2),
]


def _item_spec_ucs_c_rack_server_led():
    return TextInput(
        title=_("LED"),
        help=_("Specify the LED, for example 'Rack Unit 1 0'."),
        allow_empty=False,
    )


def _parameter_valuespec_ucs_c_rack_server_led():
    return Dictionary(
        title=_("Mapping of LED color to monitoring state"),
        help=_(
            "Define a translation of the possible LED colors to monitoring states, i.e. to the "
            "result of the check. This overwrites the default mapping used by the check."
        ),
        elements=[
            (
                color,
                MonitoringState(
                    title=_("Monitoring state if LED color is %s") % color, default_value=state
                ),
            )
            for color, state in COLORS_DEF_STATES
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ucs_c_rack_server_led",
        group=RulespecGroupCheckParametersHardware,
        item_spec=_item_spec_ucs_c_rack_server_led,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ucs_c_rack_server_led,
        title=lambda: _("Cisco UCS C-Series Rack Server LED state"),
    )
)
