#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Age, Dictionary, Float, Integer, Tuple


def _parameter_valuespec_timesyncd_time():
    return Dictionary(
        elements=[
            ("stratum_level", Integer(title=_("Critical at stratum"), default_value=10)),
            (
                "quality_levels",
                Tuple(
                    title=_("Thresholds for quality of time"),
                    elements=[
                        Float(
                            title=_("Warning at"),
                            unit=_("ms"),
                            default_value=200,
                            help=_("The offset in s at which a warning state is triggered."),
                        ),
                        Float(
                            title=_("Critical at"),
                            unit=_("ms"),
                            default_value=500,
                            help=_("The offset in s at which a critical state is triggered."),
                        ),
                    ],
                ),
            ),
            (
                "alert_delay",
                Tuple(
                    title=_("Phases without synchronization"),
                    elements=[
                        Age(
                            title=_("Warning at"),
                            display=["hours", "minutes"],
                            default_value=300,
                        ),
                        Age(
                            title=_("Critical at"),
                            display=["hours", "minutes"],
                            default_value=3600,
                        ),
                    ],
                ),
            ),
            (
                "last_synchronized",
                Tuple(
                    title=_("Allowed duration since last synchronisation"),
                    elements=[
                        Age(
                            title=_("Warning at"),
                            display=["hours", "minutes"],
                            default_value=7500,
                        ),
                        Age(
                            title=_("Critical at"),
                            display=["hours", "minutes"],
                            default_value=10800,
                        ),
                    ],
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="timesyncd_time",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_timesyncd_time,
        title=lambda: _("Systemd Timesyncd time synchronisation"),
    )
)
