#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Age, Dictionary, MonitoringState, TextInput, Tuple


def _parameter_valuespec_splunk_license_state():
    return Dictionary(
        elements=[
            ("state", MonitoringState(title=_("State if license is expired"), default_value=2)),
            (
                "expiration_time",
                Tuple(
                    title=_("Time until license expiration"),
                    help=_("Remaining days until the Windows license expires"),
                    elements=[
                        Age(title=_("Warning at"), default_value=14 * 24 * 60 * 60),
                        Age(title=_("Critical at"), default_value=7 * 24 * 60 * 60),
                    ],
                ),
            ),
        ],
        optional_keys=["state", "expiration_time", "usage_bytes"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="splunk_license_state",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of license")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_splunk_license_state,
        title=lambda: _("Splunk License State"),
    )
)
