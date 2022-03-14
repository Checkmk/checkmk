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
from cmk.gui.valuespec import (
    Age,
    Dictionary,
    DropdownChoice,
    Integer,
    MonitoringState,
    TextInput,
    Tuple,
)


def _parameter_valuespec_jenkins_nodes():
    return Dictionary(
        elements=[
            ("jenkins_offline", MonitoringState(title=_("Node state: Offline"), default_value=2)),
            (
                "jenkins_mode",
                DropdownChoice(
                    title=_("Expected mode state."),
                    help=_(
                        "Choose between Normal (Utilize this node as much "
                        "as possible) and Exclusive (Only build jobs with label "
                        "restrictions matching this node). The state will "
                        "change to warning state, if the mode differs."
                    ),
                    choices=[
                        ("NORMAL", _("Normal")),
                        ("EXCLUSIVE", _("Exclusive")),
                    ],
                    default_value="NORMAL",
                ),
            ),
            (
                "jenkins_numexecutors",
                Tuple(
                    title=_("Lower level for number of executors of this node"),
                    elements=[
                        Integer(title=_("Warning below")),
                        Integer(title=_("Critical below")),
                    ],
                ),
            ),
            (
                "jenkins_busyexecutors",
                Tuple(
                    title=_("Upper level for number of busy executors of this node"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "jenkins_idleexecutors",
                Tuple(
                    title=_("Upper level for number of idle executors of this node"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "avg_response_time",
                Tuple(
                    title=_("Average round-trip response time to this node"),
                    elements=[
                        Age(title=_("Warning at")),
                        Age(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "jenkins_clock",
                Tuple(
                    title=_("Clock difference"),
                    elements=[
                        Age(title=_("Warning at")),
                        Age(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "jenkins_temp",
                Tuple(
                    title=_("Absolute levels for free temp space"),
                    elements=[
                        Integer(
                            title=_("Warning if below"),
                            unit=_("MB"),
                            minvalue=0,
                        ),
                        Integer(
                            title=_("Critical if below"),
                            unit=_("MB"),
                            minvalue=0,
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jenkins_nodes",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Node name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jenkins_nodes,
        title=lambda: _("Jenkins nodes"),
    )
)
