#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import enum

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Float, Integer, Tuple


class MessageType(enum.StrEnum):
    """Watch out! The values must match the check plug-in!

    For now copy'n'paste. Should go to cmk/plugins/rabbitmq sometay (TM).
    """

    TOTAL = "messages"
    TOTAL_RATE = "messages_rate"
    READY = "messages_ready"
    UNACKNOWLEDGED = "messages_unacknowledged"
    PUBLISH = "messages_publish"
    PUBLISH_RATE = "messages_publish_rate"
    DELIVER = "messages_deliver"
    DELIVER_RATE = "messages_deliver_rate"


def _parameter_valuespec_rabbitmq_cluster_messages() -> Dictionary:
    return Dictionary(
        elements=[
            (
                f"{MessageType.TOTAL}_upper",
                Tuple(
                    title=_("Upper level for total number of queued messages"),
                    elements=[
                        Integer(title=_("Warning at"), unit="messages"),
                        Integer(title=_("Critical at"), unit="messages"),
                    ],
                ),
            ),
            (
                f"{MessageType.TOTAL}_lower",
                Tuple(
                    title=_("Lower level for total number of queued messages"),
                    elements=[
                        Integer(title=_("Warning below"), unit="messages"),
                        Integer(title=_("Critical below"), unit="messages"),
                    ],
                ),
            ),
            (
                f"{MessageType.TOTAL_RATE}_upper",
                Tuple(
                    title=_("Upper level for message rate"),
                    elements=[
                        Float(title=_("Warning at"), unit="1/s"),
                        Float(title=_("Critical at"), unit="1/s"),
                    ],
                ),
            ),
            (
                f"{MessageType.TOTAL_RATE}_lower",
                Tuple(
                    title=_("Lower level for message rate"),
                    elements=[
                        Float(title=_("Warning below"), unit="1/s"),
                        Float(title=_("Critical below"), unit="1/s"),
                    ],
                ),
            ),
            (
                f"{MessageType.READY}_upper",
                Tuple(
                    title=_("Upper level for total number of ready messages"),
                    elements=[
                        Integer(title=_("Warning at"), unit="messages"),
                        Integer(title=_("Critical at"), unit="messages"),
                    ],
                ),
            ),
            (
                f"{MessageType.READY}_lower",
                Tuple(
                    title=_("Lower level for total number of ready messages"),
                    elements=[
                        Integer(title=_("Warning below"), unit="messages"),
                        Integer(title=_("Critical below"), unit="messages"),
                    ],
                ),
            ),
            (
                f"{MessageType.UNACKNOWLEDGED}_upper",
                Tuple(
                    title=_("Upper level for total number of unacknowledged messages"),
                    elements=[
                        Integer(title=_("Warning at"), unit="messages"),
                        Integer(title=_("Critical at"), unit="messages"),
                    ],
                ),
            ),
            (
                f"{MessageType.UNACKNOWLEDGED}_lower",
                Tuple(
                    title=_("Lower level for total number of unacknowledged messages"),
                    elements=[
                        Integer(title=_("Warning below"), unit="messages"),
                        Integer(title=_("Critical below"), unit="messages"),
                    ],
                ),
            ),
            (
                f"{MessageType.PUBLISH}_upper",
                Tuple(
                    title=_("Upper level for total number of published messages"),
                    elements=[
                        Integer(title=_("Warning at"), unit="messages"),
                        Integer(title=_("Critical at"), unit="messages"),
                    ],
                ),
            ),
            (
                f"{MessageType.PUBLISH}_lower",
                Tuple(
                    title=_("Lower level for total number of published messages"),
                    elements=[
                        Integer(title=_("Warning below"), unit="messages"),
                        Integer(title=_("Critical below"), unit="messages"),
                    ],
                ),
            ),
            (
                f"{MessageType.PUBLISH_RATE}_upper",
                Tuple(
                    title=_("Upper level for published message rate"),
                    elements=[
                        Float(title=_("Warning at"), unit="1/s"),
                        Float(title=_("Critical at"), unit="1/s"),
                    ],
                ),
            ),
            (
                f"{MessageType.PUBLISH_RATE}_lower",
                Tuple(
                    title=_("Lower level for published message rate"),
                    elements=[
                        Float(title=_("Warning below"), unit="1/s"),
                        Float(title=_("Critical below"), unit="1/s"),
                    ],
                ),
            ),
            (
                f"{MessageType.DELIVER}_upper",
                Tuple(
                    title=_("Upper level for total number of delivered messages"),
                    elements=[
                        Integer(title=_("Warning at"), unit="messages"),
                        Integer(title=_("Critical at"), unit="messages"),
                    ],
                ),
            ),
            (
                f"{MessageType.DELIVER}_lower",
                Tuple(
                    title=_("Lower level for total number of delivered messages"),
                    elements=[
                        Integer(title=_("Warning below"), unit="messages"),
                        Integer(title=_("Critical below"), unit="messages"),
                    ],
                ),
            ),
            (
                f"{MessageType.DELIVER_RATE}_rate_upper",
                Tuple(
                    title=_("Upper level for delivered message rate"),
                    elements=[
                        Float(title=_("Warning at"), unit="1/s"),
                        Float(title=_("Critical at"), unit="1/s"),
                    ],
                ),
            ),
            (
                f"{MessageType.DELIVER_RATE}_lower",
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
    CheckParameterRulespecWithoutItem(
        check_group_name="rabbitmq_cluster_messages",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_rabbitmq_cluster_messages,
        title=lambda: _("RabbitMQ cluster messages"),
    )
)
