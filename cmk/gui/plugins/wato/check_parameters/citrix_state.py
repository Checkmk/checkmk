#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, MonitoringState


def _parameter_valuespec_citrix_state():
    return Dictionary(
        elements=[
            (
                "registrationstate",
                Dictionary(
                    title=_("Interpretation of Registration States"),
                    elements=[
                        ("Unregistered", MonitoringState(title=_("Unregistered"), default_value=2)),
                        ("Initializing", MonitoringState(title=_("Initializing"), default_value=1)),
                        ("Registered", MonitoringState(title=_("Registered"), default_value=0)),
                        ("AgentError", MonitoringState(title=_("Agent Error"), default_value=2)),
                    ],
                    optional_keys=False,
                ),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="citrix_state",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_citrix_state,
        title=lambda: _("Citrix VM state"),
    )
)
