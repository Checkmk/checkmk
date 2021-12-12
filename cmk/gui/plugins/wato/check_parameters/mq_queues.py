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
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _item_spec_mq_queues():
    return TextInput(
        title=_("Queue Name"), help=_("The name of the queue like in the Apache queue manager")
    )


def _parameter_valuespec_mq_queues():
    return Dictionary(
        elements=[
            (
                "size",
                Tuple(
                    title=_("Levels for the queue length"),
                    help=_("Set the maximum and minimum length for the queue size"),
                    elements=[
                        Integer(title="Warning at a size of"),
                        Integer(title="Critical at a size of"),
                    ],
                ),
            ),
            (
                "consumerCount",
                Tuple(
                    title=_("Levels for the consumer count"),
                    help=_("Consumer Count is the size of connected consumers to a queue"),
                    elements=[
                        Integer(title="Warning less then"),
                        Integer(title="Critical less then"),
                    ],
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
