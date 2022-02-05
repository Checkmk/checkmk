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


def _parameter_valuespec_rabbitmq_cluster_stats():
    return Dictionary(
        elements=[
            (
                "channels_upper",
                Tuple(
                    title=_("Upper level for total number of channels"),
                    elements=[
                        Integer(title=_("Warning at"), unit="channels"),
                        Integer(title=_("Critical at"), unit="channels"),
                    ],
                ),
            ),
            (
                "channels_lower",
                Tuple(
                    title=_("Lower level for total number of channels"),
                    elements=[
                        Integer(title=_("Warning below"), unit="channels"),
                        Integer(title=_("Critical below"), unit="channels"),
                    ],
                ),
            ),
            (
                "connections_upper",
                Tuple(
                    title=_("Upper level for total number of connections"),
                    elements=[
                        Integer(title=_("Warning at"), unit="connections"),
                        Integer(title=_("Critical at"), unit="connections"),
                    ],
                ),
            ),
            (
                "connections_lower",
                Tuple(
                    title=_("Lower level for total number of connections"),
                    elements=[
                        Integer(title=_("Warning below"), unit="connections"),
                        Integer(title=_("Critical below"), unit="connections"),
                    ],
                ),
            ),
            (
                "consumers_upper",
                Tuple(
                    title=_("Upper level for total number of consumers"),
                    elements=[
                        Integer(title=_("Warning at"), unit="consumers"),
                        Integer(title=_("Critical at"), unit="consumers"),
                    ],
                ),
            ),
            (
                "consumers_lower",
                Tuple(
                    title=_("Lower level for total number of consumers"),
                    elements=[
                        Integer(title=_("Warning below"), unit="consumers"),
                        Integer(title=_("Critical below"), unit="consumers"),
                    ],
                ),
            ),
            (
                "exchanges_upper",
                Tuple(
                    title=_("Upper level for total number of exchanges"),
                    elements=[
                        Integer(title=_("Warning at"), unit="exchanges"),
                        Integer(title=_("Critical at"), unit="exchanges"),
                    ],
                ),
            ),
            (
                "exchanges_lower",
                Tuple(
                    title=_("Lower level for total number of exchanges"),
                    elements=[
                        Integer(title=_("Warning below"), unit="exchanges"),
                        Integer(title=_("Critical below"), unit="exchanges"),
                    ],
                ),
            ),
            (
                "queues_upper",
                Tuple(
                    title=_("Upper level for total number of queues"),
                    elements=[
                        Integer(title=_("Warning at"), unit="queues"),
                        Integer(title=_("Critical at"), unit="queues"),
                    ],
                ),
            ),
            (
                "queues_lower",
                Tuple(
                    title=_("Lower level for total number of queues"),
                    elements=[
                        Integer(title=_("Warning below"), unit="queues"),
                        Integer(title=_("Critical below"), unit="queues"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="rabbitmq_cluster_stats",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_rabbitmq_cluster_stats,
        title=lambda: _("RabbitMQ cluster stats"),
    )
)
