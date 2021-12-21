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


def _parameter_valuespec_fireeye_mailq():
    return Dictionary(
        elements=[
            (
                "deferred",
                Tuple(
                    title=_("Levels for Deferred Queue length"),
                    elements=[
                        Integer(title="Warning at", default_value=10, unit="Mails"),
                        Integer(title="Critical at", default_value=15, unit="Mails"),
                    ],
                ),
            ),
            (
                "hold",
                Tuple(
                    title=_("Levels for Hold Queue length"),
                    elements=[
                        Integer(title="Warning at", default_value=500, unit="Mails"),
                        Integer(title="Critical at", default_value=700, unit="Mails"),
                    ],
                ),
            ),
            (
                "drop",
                Tuple(
                    title=_("Levels for Drop Queue length"),
                    elements=[
                        Integer(title="Warning at", default_value=10, unit="Mails"),
                        Integer(title="Critical at", default_value=15, unit="Mails"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="fireeye_mailq",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fireeye_mailq,
        title=lambda: _("Fireeye Mail Queues"),
    )
)
