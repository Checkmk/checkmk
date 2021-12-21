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
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_splunk_alerts():
    return Dictionary(
        elements=[
            (
                "alerts",
                Tuple(
                    title=_("Upper levels for number of alerts"),
                    elements=[
                        Integer(title=_("Warning at"), minvalue=0),
                        Integer(title=_("Critical at"), minvalue=0),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="splunk_alerts",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_splunk_alerts,
        title=lambda: _("Splunk Alerts"),
    )
)
