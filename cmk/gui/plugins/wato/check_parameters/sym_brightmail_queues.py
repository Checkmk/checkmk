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


def _parameter_valuespec_sym_brightmail_queues():
    return Dictionary(
        help=_(
            "This check is used to monitor successful email delivery through "
            "Symantec Brightmail Scanner appliances."
        ),
        elements=[
            (
                "connections",
                Tuple(
                    title=_("Number of connections"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "messageRate",
                Tuple(
                    title=_("Number of messages delivered"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "dataRate",
                Tuple(
                    title=_("Amount of data processed"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Cricital at")),
                    ],
                ),
            ),
            (
                "queuedMessages",
                Tuple(
                    title=_("Number of messages currently queued"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "queueSize",
                Tuple(
                    title=_("Size of the queue"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "deferredMessages",
                Tuple(
                    title=_("Number of messages in deferred state"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="sym_brightmail_queues",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Instance name"), allow_empty=True),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_sym_brightmail_queues,
        title=lambda: _("Symantec Brightmail Queues"),
    )
)
