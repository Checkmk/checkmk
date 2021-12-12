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
from cmk.gui.valuespec import Age, Dictionary, Integer, MonitoringState, Tuple


def _parameter_valuespec_jenkins_queue():
    return Dictionary(
        elements=[
            (
                "queue_length",
                Tuple(
                    title=_("Upper level for queue length"),
                    elements=[
                        Integer(title=_("Warning at"), unit="Tasks"),
                        Integer(title=_("Critical at"), unit="Tasks"),
                    ],
                ),
            ),
            (
                "in_queue_since",
                Tuple(
                    title=_("Task in queue since"),
                    elements=[
                        Age(title=_("Warning at"), default_value=3600),
                        Age(title=_("Critical at"), default_value=7200),
                    ],
                ),
            ),
            (
                "stuck",
                MonitoringState(
                    title=_("Task state: Stuck"),
                    default_value=2,
                ),
            ),
            (
                "jenkins_stuck_tasks",
                Tuple(
                    title=_("Upper level for stuck tasks"),
                    elements=[
                        Integer(title=_("Warning at"), unit="Tasks", default_value=1),
                        Integer(title=_("Critical at"), unit="Tasks", default_value=2),
                    ],
                ),
            ),
            (
                "blocked",
                MonitoringState(
                    title=_("Task state: Blocked"),
                    default_value=0,
                ),
            ),
            (
                "jenkins_blocked_tasks",
                Tuple(
                    title=_("Upper level for blocked tasks"),
                    elements=[
                        Integer(title=_("Warning at"), unit="Tasks"),
                        Integer(title=_("Critical at"), unit="Tasks"),
                    ],
                ),
            ),
            ("pending", MonitoringState(title=_("Task state: Pending"), default_value=0)),
            (
                "jenkins_pending_tasks",
                Tuple(
                    title=_("Upper level for pending tasks"),
                    elements=[
                        Integer(title=_("Warning at or above"), unit="Tasks"),
                        Integer(title=_("Critical at or above"), unit="Tasks"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="jenkins_queue",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jenkins_queue,
        title=lambda: _("Jenkins queue"),
    )
)
