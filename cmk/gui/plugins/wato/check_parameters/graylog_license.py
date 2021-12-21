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
from cmk.gui.valuespec import Age, Dictionary, MonitoringState, Tuple


def _parameter_valuespec_graylog_license():
    return Dictionary(
        elements=[
            (
                "no_enterprise",
                MonitoringState(
                    title=_("State when no enterprise license is installed"), default_value=0
                ),
            ),
            ("expired", MonitoringState(title=_("State when license is expired"), default_value=2)),
            (
                "violated",
                MonitoringState(title=_("State when license state is violated"), default_value=2),
            ),
            ("valid", MonitoringState(title=_("State when license is not valid"), default_value=2)),
            (
                "traffic_exceeded",
                MonitoringState(title=_("State when license traffic is exceeded"), default_value=1),
            ),
            (
                "cluster_not_covered",
                MonitoringState(
                    title=_("State when license does not cover cluster"), default_value=1
                ),
            ),
            (
                "nodes_exceeded",
                MonitoringState(title=_("State when license nodes exceeded"), default_value=1),
            ),
            (
                "remote_checks_failed",
                MonitoringState(title=_("State when license remote check failed"), default_value=1),
            ),
            (
                "expiration",
                Tuple(
                    title=_("Time until license expiration"),
                    help=_("Remaining days until the Graylog license expires"),
                    elements=[
                        Age(title=_("Warning at"), default_value=14 * 24 * 60 * 60),
                        Age(title=_("Critical at"), default_value=7 * 24 * 60 * 60),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="graylog_license",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_graylog_license,
        title=lambda: _("Graylog license"),
    )
)
