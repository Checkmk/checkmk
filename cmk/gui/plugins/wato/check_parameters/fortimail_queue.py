#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _parameter_valuespec_fortimail_queue():
    return Dictionary(
        elements=[
            (
                "queue_length",
                Tuple(
                    elements=[
                        Integer(
                            title=_("Warning at"),
                            unit=_("mails"),
                            default_value=100,
                        ),
                        Integer(
                            title=_("Critical at"),
                            unit=_("mails"),
                            default_value=200,
                        ),
                    ],
                    title=_("Levels for queue length"),
                    help=_("Define levels on the queue length."),
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fortimail_queue",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(
            title=_("Queue Name"),
        ),
        parameter_valuespec=_parameter_valuespec_fortimail_queue,
        title=lambda: _("Fortinet FortiMail queue length"),
    )
)
