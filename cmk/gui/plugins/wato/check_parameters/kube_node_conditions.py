#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, MonitoringState


# TODO: change valuespec in a way to support user-defined type-to-state mappings
def _parameter_valuespec():
    return Dictionary(
        elements=[
            (
                "ready",
                MonitoringState(
                    title=_("Monitoring state if the READY condition is faulty or not available"),
                    default_value=2,
                ),
            ),
            (
                "memorypressure",
                MonitoringState(
                    title=_(
                        "Monitoring state if the MEMORYPRESSURE condition is faulty or not available"
                    ),
                    default_value=2,
                ),
            ),
            (
                "diskpressure",
                MonitoringState(
                    title=_(
                        "Monitoring state if the DISKPRESSURE condition is faulty or not available"
                    ),
                    default_value=2,
                ),
            ),
            (
                "pidpressure",
                MonitoringState(
                    title=_(
                        "Monitoring state if the PIDPRESSURE condition is faulty or not available"
                    ),
                    default_value=2,
                ),
            ),
            (
                "networkunavailable",
                MonitoringState(
                    title=_(
                        "Monitoring state if the NETWORKUNAVAILABLE condition is faulty or not available"
                    ),
                    default_value=2,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_node_conditions",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec,
        title=lambda: _("Node conditions"),
    )
)
