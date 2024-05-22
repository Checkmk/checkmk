#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Float, Integer, Migrate, Tuple


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


_KEY_MAP = {
    "message_rate_upper": f"{MessageType.TOTAL_RATE}_upper",
    "message_rate_lower": f"{MessageType.TOTAL_RATE}_lower",
    "msg_ready_upper": f"{MessageType.READY}_upper",
    "msg_ready_lower": f"{MessageType.READY}_lower",
    "msg_unack_upper": f"{MessageType.UNACKNOWLEDGED}_upper",
    "msg_unack_lower": f"{MessageType.UNACKNOWLEDGED}_lower",
    "msg_publish_upper": f"{MessageType.PUBLISH}_upper",
    "msg_publish_lower": f"{MessageType.PUBLISH}_lower",
    "msg_publish_rate_upper": f"{MessageType.PUBLISH_RATE}_upper",
    "msg_publish_rate_lower": f"{MessageType.PUBLISH_RATE}_lower",
    "msg_deliver_upper": f"{MessageType.DELIVER}_upper",
    "msg_deliver_lower": f"{MessageType.DELIVER}_lower",
    "msg_deliver_rate_upper": f"{MessageType.DELIVER_RATE}_upper",
    "msg_deliver_rate_lower": f"{MessageType.DELIVER_RATE}_lower",
}


def _rename_keys(p: dict[str, object]) -> dict[str, object]:
    """The plug-in really needs these keys."""
    return {_KEY_MAP.get(k, k): v for k, v in p.items()}


def _parameter_valuespec_rabbitmq_cluster_messages():
    return Migrate(
        valuespec=Dictionary(
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
        ),
        migrate=_rename_keys,
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
