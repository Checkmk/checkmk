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
from cmk.gui.valuespec import Dictionary, Float, Integer, TextInput, Tuple


def _parameter_valuespec_rabbitmq_vhosts():
    return Dictionary(
        elements=[
            (
                "msg_upper",
                Tuple(
                    title=_("Upper level for total number of messages"),
                    elements=[
                        Integer(title=_("Warning at"), unit="messages"),
                        Integer(title=_("Critical at"), unit="messages"),
                    ],
                ),
            ),
            (
                "msg_lower",
                Tuple(
                    title=_("Lower level for total number of messages"),
                    elements=[
                        Integer(title=_("Warning below"), unit="messages"),
                        Integer(title=_("Critical below"), unit="messages"),
                    ],
                ),
            ),
            (
                "msg_ready_upper",
                Tuple(
                    title=_("Upper level for total number of ready messages"),
                    elements=[
                        Integer(title=_("Warning at"), unit="messages"),
                        Integer(title=_("Critical at"), unit="messages"),
                    ],
                ),
            ),
            (
                "msg_ready_lower",
                Tuple(
                    title=_("Lower level for total number of ready messages"),
                    elements=[
                        Integer(title=_("Warning below"), unit="messages"),
                        Integer(title=_("Critical below"), unit="messages"),
                    ],
                ),
            ),
            (
                "msg_unack_upper",
                Tuple(
                    title=_("Upper level for total number of unacknowledged messages"),
                    elements=[
                        Integer(title=_("Warning at"), unit="messages"),
                        Integer(title=_("Critical at"), unit="messages"),
                    ],
                ),
            ),
            (
                "msg_unack_lower",
                Tuple(
                    title=_("Lower level for total number of unacknowledged messages"),
                    elements=[
                        Integer(title=_("Warning below"), unit="messages"),
                        Integer(title=_("Critical below"), unit="messages"),
                    ],
                ),
            ),
            (
                "msg_publish_upper",
                Tuple(
                    title=_("Upper level for total number of published messages"),
                    elements=[
                        Integer(title=_("Warning at"), unit="messages"),
                        Integer(title=_("Critical at"), unit="messages"),
                    ],
                ),
            ),
            (
                "msg_publish_lower",
                Tuple(
                    title=_("Lower level for total number of published messages"),
                    elements=[
                        Integer(title=_("Warning below"), unit="messages"),
                        Integer(title=_("Critical below"), unit="messages"),
                    ],
                ),
            ),
            (
                "msg_publish_rate_upper",
                Tuple(
                    title=_("Upper level for published message rate"),
                    elements=[
                        Float(title=_("Warning at"), unit="1/s"),
                        Float(title=_("Critical at"), unit="1/s"),
                    ],
                ),
            ),
            (
                "msg_publish_rate_lower",
                Tuple(
                    title=_("Lower level for published message rate"),
                    elements=[
                        Float(title=_("Warning below"), unit="1/s"),
                        Float(title=_("Critical below"), unit="1/s"),
                    ],
                ),
            ),
            (
                "msg_deliver_upper",
                Tuple(
                    title=_("Upper level for total number of delivered messages"),
                    elements=[
                        Integer(title=_("Warning at"), unit="messages"),
                        Integer(title=_("Critical at"), unit="messages"),
                    ],
                ),
            ),
            (
                "msg_deliver_lower",
                Tuple(
                    title=_("Lower level for total number of delivered messages"),
                    elements=[
                        Integer(title=_("Warning below"), unit="messages"),
                        Integer(title=_("Critical below"), unit="messages"),
                    ],
                ),
            ),
            (
                "msg_deliver_rate_upper",
                Tuple(
                    title=_("Upper level for delivered message rate"),
                    elements=[
                        Float(title=_("Warning at"), unit="1/s"),
                        Float(title=_("Critical at"), unit="1/s"),
                    ],
                ),
            ),
            (
                "msg_deliver_rate_lower",
                Tuple(
                    title=_("Lower level for delivered message rate"),
                    elements=[
                        Float(title=_("Warning below"), unit="1/s"),
                        Float(title=_("Critical below"), unit="1/s"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="rabbitmq_vhosts",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Vhost name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_rabbitmq_vhosts,
        title=lambda: _("RabbitMQ vhosts"),
    )
)
