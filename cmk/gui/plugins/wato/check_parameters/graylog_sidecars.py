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
from cmk.gui.valuespec import Age, Dictionary, Integer, MonitoringState, TextInput, Tuple


def _parameter_valuespec_graylog_sidecars():
    return Dictionary(
        elements=[
            (
                "active_state",
                MonitoringState(title=_("State when active state is not OK"), default_value=2),
            ),
            (
                "last_seen",
                Tuple(
                    title=_("Time since the sidecar was last seen by graylog"),
                    elements=[Age(title=_("Warning at")), Age(title=_("Critical at"))],
                ),
            ),
            (
                "running_lower",
                Tuple(
                    title=_("Total number of collectors in state running lower level"),
                    elements=[
                        Integer(
                            title=_("Warning if less then"), unit="collectors", default_value=1
                        ),
                        Integer(
                            title=_("Critical if less then"), unit="collectors", default_value=0
                        ),
                    ],
                ),
            ),
            (
                "running_upper",
                Tuple(
                    title=_("Total number of collectors in state running upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="collectors"),
                        Integer(title=_("Critical at"), unit="collectors"),
                    ],
                ),
            ),
            (
                "stopped_lower",
                Tuple(
                    title=_("Total number of collectors in state stopped lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="collectors"),
                        Integer(title=_("Critical if less then"), unit="collectors"),
                    ],
                ),
            ),
            (
                "stopped_upper",
                Tuple(
                    title=_("Total number of collectors in state stopped upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="collectors", default_value=1),
                        Integer(title=_("Critical at"), unit="collectors", default_value=1),
                    ],
                ),
            ),
            (
                "failing_lower",
                Tuple(
                    title=_("Total number of collectors in state failing lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="collectors"),
                        Integer(title=_("Critical if less then"), unit="collectors"),
                    ],
                ),
            ),
            (
                "failing_upper",
                Tuple(
                    title=_("Total number of collectors in state failing upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="collectors", default_value=1),
                        Integer(title=_("Critical at"), unit="collectors", default_value=1),
                    ],
                ),
            ),
            (
                "running",
                MonitoringState(
                    title=_("State when collector is in state running"), default_value=0
                ),
            ),
            (
                "stopped",
                MonitoringState(
                    title=_("State when collector is in state stopped"), default_value=1
                ),
            ),
            (
                "failing",
                MonitoringState(
                    title=_("State when collector is in state failing"), default_value=2
                ),
            ),
            (
                "no_ping",
                MonitoringState(title=_("State when no ping signal from sidecar"), default_value=2),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="graylog_sidecars",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Sidecar name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_graylog_sidecars,
        title=lambda: _("Graylog sidecars"),
    )
)
