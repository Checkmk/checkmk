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
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput


def _parameter_valuespec_hp_hh3c_ext_states():
    return Dictionary(
        elements=[
            (
                "oper",
                Dictionary(
                    title=_("Operational states"),
                    elements=[
                        (
                            "not_supported",
                            MonitoringState(title=_("Not supported"), default_value=1),
                        ),
                        ("disabled", MonitoringState(title=_("Disabled"), default_value=2)),
                        ("enabled", MonitoringState(title=_("Enabled"), default_value=0)),
                        ("dangerous", MonitoringState(title=_("Dangerous"), default_value=2)),
                    ],
                ),
            ),
            (
                "admin",
                Dictionary(
                    title=_("Administrative states"),
                    elements=[
                        (
                            "not_supported",
                            MonitoringState(title=_("Not supported"), default_value=1),
                        ),
                        ("locked", MonitoringState(title=_("Locked"), default_value=0)),
                        (
                            "shutting_down",
                            MonitoringState(title=_("Shutting down"), default_value=2),
                        ),
                        ("unlocked", MonitoringState(title=_("Unlocked"), default_value=2)),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="hp_hh3c_ext_states",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("Port"), help=_("The Port Description")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_hp_hh3c_ext_states,
        title=lambda: _("HP Switch module state"),
    )
)
