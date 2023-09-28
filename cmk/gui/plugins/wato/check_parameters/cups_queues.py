#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersPrinters,
)
from cmk.gui.valuespec import Dictionary, Integer, MonitoringState, TextInput, Tuple


def _parameter_valuespec_cups_queues():
    return Dictionary(
        elements=[
            (
                "job_count",
                Tuple(
                    title=_("Levels of current jobs"),
                    elements=[
                        Integer(title=_("Warning at"), default_value=5),
                        Integer(title=_("Critical at"), default_value=10),
                    ],
                ),
            ),
            (
                "job_age",
                Tuple(
                    title=_("Levels for age of jobs"),
                    help=_("A value in seconds"),
                    elements=[
                        Integer(title=_("Warning at"), default_value=360),
                        Integer(title=_("Critical at"), default_value=720),
                    ],
                ),
            ),
            (
                "is_idle",
                MonitoringState(
                    title=_("State for 'is idle'"),
                    default_value=0,
                ),
            ),
            (
                "now_printing",
                MonitoringState(
                    title=_("State for 'now printing'"),
                    default_value=0,
                ),
            ),
            (
                "disabled_since",
                MonitoringState(
                    title=_("State for 'disabled since'"),
                    default_value=2,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="cups_queues",
        group=RulespecGroupCheckParametersPrinters,
        item_spec=lambda: TextInput(title=_("CUPS Queue")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cups_queues,
        title=lambda: _("CUPS Queue"),
    )
)
