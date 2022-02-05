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


def _parameter_valuespec_splunk_health():
    return Dictionary(
        help=_(
            "You can specify a separate monitoring state for each "
            "possible combination of service state."
        ),
        elements=[
            (
                "green",
                MonitoringState(
                    title=_("Status: green"),
                    default_value=0,
                ),
            ),
            (
                "yellow",
                MonitoringState(
                    title=_("Status: yellow"),
                    default_value=1,
                ),
            ),
            (
                "red",
                MonitoringState(
                    title=_("Status: red"),
                    default_value=2,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="splunk_health",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_splunk_health,
        title=lambda: _("Splunk Health"),
    )
)
