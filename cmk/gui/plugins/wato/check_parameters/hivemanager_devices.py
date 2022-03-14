#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Age, Dictionary, FixedValue, Integer, ListChoice, TextInput, Tuple

hivemanger_states = [
    ("Critical", "Critical"),
    ("Maybe", "Maybe"),
    ("Major", "Major"),
    ("Minor", "Minor"),
]


def _parameter_valuespec_hivemanager_devices():
    return Dictionary(
        elements=[
            (
                "max_clients",
                Tuple(
                    title=_("Number of clients"),
                    help=_("Number of clients connected to a Device."),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("clients")),
                        Integer(title=_("Critical at"), unit=_("clients")),
                    ],
                ),
            ),
            (
                "max_uptime",
                Tuple(
                    title=_("Maximum uptime of Device"),
                    elements=[
                        Age(title=_("Warning at")),
                        Age(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "alert_on_loss",
                FixedValue(
                    value=False,
                    totext="",
                    title=_("Do not alert on connection loss"),
                ),
            ),
            (
                "warn_states",
                ListChoice(
                    title=_("States treated as warning"),
                    choices=hivemanger_states,
                    default_value=["Maybe", "Major", "Minor"],
                ),
            ),
            (
                "crit_states",
                ListChoice(
                    title=_("States treated as critical"),
                    choices=hivemanger_states,
                    default_value=["Critical"],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="hivemanager_devices",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("Hostname of the Device")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_hivemanager_devices,
        title=lambda: _("Hivemanager Devices"),
    )
)
