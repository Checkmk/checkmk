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
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput


def _parameter_valuespec_rabbitmq_nodes():
    return Dictionary(
        elements=[
            (
                "state",
                MonitoringState(title=_("State if node is not in state running"), default_value=2),
            ),
            (
                "disk_free_alarm",
                MonitoringState(
                    title=_("State if node has disk free alarm in effect"), default_value=2
                ),
            ),
            (
                "mem_alarm",
                MonitoringState(title=_("State if node has mem alarm in effect"), default_value=2),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="rabbitmq_nodes",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Node name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_rabbitmq_nodes,
        title=lambda: _("RabbitMQ nodes"),
    )
)
