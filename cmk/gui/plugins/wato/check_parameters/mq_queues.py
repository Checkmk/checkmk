#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Integer, TextInput


def _item_spec_mq_queues():
    return TextInput(
        title=_("Queue Name"), help=_("The name of the queue like in the Apache queue manager")
    )


def _migrate_mq_queue_consumer_count_levels(
    in_params: Mapping[str, object],
) -> Mapping[str, object]:
    """Migrate legacy consumerCount levels to separate upper/lower level fields.

    The legacy consumerCount tuple (warn, crit) is interpreted as:
    - upper levels if crit > warn
    - lower levels if warn > crit

    Non-tuple or malformed values are ignored.
    """
    match in_params:
        case {"consumerCount": tuple((int(), int())) as levels, **rest}:
            direction = "upper" if levels[1] > levels[0] else "lower"
            return {
                f"consumer_count_levels_{direction}": levels,
                **rest,
            }
        case other:
            return other


def _parameter_valuespec_mq_queues():
    return Dictionary(
        migrate=_migrate_mq_queue_consumer_count_levels,  # type: ignore[arg-type]
        elements=[
            (
                "size",
                SimpleLevels(
                    title=_("Levels for the queue length"),
                    help=_("Set the maximum and minimum length for the queue size"),
                    spec=Integer,
                ),
            ),
            (
                "consumer_count_levels_upper",
                SimpleLevels(
                    title=_("Upper Levels for the consumer count"),
                    help=_("Consumer Count is the size of connected consumers to a queue"),
                    spec=Integer,
                    direction="upper",
                ),
            ),
            (
                "consumer_count_levels_lower",
                SimpleLevels(
                    title=_("Lower levels for the consumer count"),
                    help=_("Consumer Count is the size of connected consumers to a queue"),
                    spec=Integer,
                    direction="lower",
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mq_queues",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_mq_queues,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mq_queues,
        title=lambda: _("Apache ActiveMQ Queue lengths"),
    )
)
