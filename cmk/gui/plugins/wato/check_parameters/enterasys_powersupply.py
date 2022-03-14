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
from cmk.gui.valuespec import Dictionary, ListChoice, TextInput


def _parameter_valuespec_enterasys_powersupply():
    return Dictionary(
        elements=[
            (
                "redundancy_ok_states",
                ListChoice(
                    title=_("States treated as OK"),
                    choices=[
                        (1, "redundant"),
                        (2, "notRedundant"),
                        (3, "notSupported"),
                    ],
                    default_value=[1],
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="enterasys_powersupply",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(
            title=_("Number of Powersupply"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_enterasys_powersupply,
        title=lambda: _("Enterasys Power Supply Settings"),
    )
)
