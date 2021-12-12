#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput


def _parameter_valuespec_iis_app_pool_state():
    return Dictionary(
        required_keys=["state_mapping"],
        elements=[
            (
                "state_mapping",
                Dictionary(
                    title="Map of Application Pool States to Service States",
                    optional_keys=[],
                    elements=[
                        ("Uninitialized", MonitoringState(default_value=2, title="Uninitialized")),
                        ("Initialized", MonitoringState(default_value=1, title="Initialized")),
                        ("Running", MonitoringState(default_value=0, title="Running")),
                        ("Disabling", MonitoringState(default_value=2, title="Disabling")),
                        ("Disabled", MonitoringState(default_value=2, title="Disabled")),
                        (
                            "ShutdownPending",
                            MonitoringState(default_value=2, title="ShutdownPending"),
                        ),
                        ("DeletePending", MonitoringState(default_value=2, title="DeletePending")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="iis_app_pool_state",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        item_spec=lambda: TextInput(title=_("Application Pool name")),
        parameter_valuespec=_parameter_valuespec_iis_app_pool_state,
        title=lambda: _("IIS Application Pool State Settings"),
    )
)
