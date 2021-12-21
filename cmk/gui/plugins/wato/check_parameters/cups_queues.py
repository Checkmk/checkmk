#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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
                    default_value=(5, 10),
                    elements=[Integer(title=_("Warning at")), Integer(title=_("Critical at"))],
                ),
            ),
            (
                "job_age",
                Tuple(
                    title=_("Levels for age of jobs"),
                    help=_("A value in seconds"),
                    default_value=(360, 720),
                    elements=[Integer(title=_("Warning at")), Integer(title=_("Critical at"))],
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
