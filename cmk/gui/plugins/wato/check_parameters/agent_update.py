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


def _parameter_valuespec_check_mk_agent_update():
    return Dictionary(
        elements=[
            (
                "error_deployment_globally_disabled",
                MonitoringState(
                    title=_("State if agent deployment is globally disabled"), default_value=1
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="agent_update",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_check_mk_agent_update,
        title=lambda: _("Agent update"),
    )
)
