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
from cmk.gui.valuespec import Dictionary, Integer, MonitoringState, Tuple


def _parameter_valuespec_graylog_streams():
    return Dictionary(
        elements=[
            (
                "stream_count_lower",
                Tuple(
                    title=_("Total number of streams lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="streams"),
                        Integer(title=_("Critical if less then"), unit="streams"),
                    ],
                ),
            ),
            (
                "stream_count_upper",
                Tuple(
                    title=_("Total number of streams upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="streams"),
                        Integer(title=_("Critical at"), unit="streams"),
                    ],
                ),
            ),
            (
                "stream_disabled",
                MonitoringState(
                    title=_("State when one of the streams is in state disabled"), default_value=1
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="graylog_streams",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_graylog_streams,
        title=lambda: _("Graylog streams"),
    )
)
