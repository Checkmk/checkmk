#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Tuple as _Tuple

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    FixedValue,
    Float,
    ListChoice,
    TextInput,
    Tuple,
)


def _vs_cisco_dom(which_levels: str) -> _Tuple[str, Alternative]:
    def _button_text_warn(which_levels: str) -> str:
        if which_levels == "upper":
            text = _("Warning at")
        elif which_levels == "lower":
            text = _("Warning below")
        else:
            raise ValueError()
        return text

    def _button_text_crit(which_levels: str) -> str:
        if which_levels == "upper":
            text = _("Critical at")
        elif which_levels == "lower":
            text = _("Critical below")
        else:
            raise ValueError()
        return text

    return (
        "power_levels_%s" % which_levels,
        Alternative(
            title="%s levels for the signal power" % which_levels.title(),
            default_value=True,  # use device levels
            elements=[
                FixedValue(
                    value=True,
                    title=_("Use device levels"),
                    totext="",
                ),
                Tuple(
                    title=_("Use the following levels"),
                    elements=[
                        Float(title=_button_text_warn(which_levels), unit=_("dBm")),
                        Float(title=_button_text_crit(which_levels), unit=_("dBm")),
                    ],
                ),
                FixedValue(
                    value=False,
                    title=_("No levels"),
                    totext="",
                ),
            ],
        ),
    )


def _item_spec_cisco_dom() -> TextInput:
    return TextInput(title=_("Sensor description if present, sensor index otherwise"))


def _parameter_valuespec_cisco_dom() -> Dictionary:
    return Dictionary(
        elements=[
            (_vs_cisco_dom("upper")),
            (_vs_cisco_dom("lower")),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="cisco_dom",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_cisco_dom,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cisco_dom,
        title=lambda: _("CISCO Digital Optical Monitoring (DOM)"),
    )
)


def _valuespec_discovery_cisco_dom_rules():
    return Dictionary(
        title=_("Cisco DOM discovery"),
        elements=[
            (
                "admin_states",
                ListChoice(
                    title=_("Admin states to discover"),
                    choices={
                        1: _("up"),
                        2: _("down"),
                        3: _("testing"),
                    },
                    toggle_all=True,
                    default_value=["1", "2", "3"],
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="discovery_cisco_dom_rules",
        valuespec=_valuespec_discovery_cisco_dom_rules,
    )
)
