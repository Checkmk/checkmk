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
from cmk.gui.valuespec import Age, Dictionary, TextInput, Tuple


def _parameter_valuespec_rabbitmq_nodes_uptime():
    return Dictionary(
        elements=[
            (
                "min",
                Tuple(
                    title=_("Minimum required uptime"),
                    elements=[
                        Age(title=_("Warning if below")),
                        Age(title=_("Critical if below")),
                    ],
                ),
            ),
            (
                "max",
                Tuple(
                    title=_("Maximum allowed uptime"),
                    elements=[
                        Age(title=_("Warning at")),
                        Age(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="rabbitmq_nodes_uptime",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Node name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_rabbitmq_nodes_uptime,
        title=lambda: _("RabbitMQ nodes uptime"),
    )
)
