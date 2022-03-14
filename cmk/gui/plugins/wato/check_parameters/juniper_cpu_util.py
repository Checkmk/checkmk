#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Dictionary, Percentage, TextInput, Transform, Tuple


def _parameter_valuespec_juniper_cpu_util():
    return Transform(
        valuespec=Dictionary(
            optional_keys=[],
            elements=[
                (
                    "levels",
                    Tuple(
                        title=_("Upper levels"),
                        elements=[
                            Percentage(title=_("Warning at"), default_value=80.0),
                            Percentage(title=_("Critical at"), default_value=90.0),
                        ],
                    ),
                ),
            ],
        ),
        forth=lambda old: not old and {"levels": (80.0, 90.0)} or old,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="juniper_cpu_util",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=lambda: TextInput(
            title=_("Operating CPU"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_juniper_cpu_util,
        title=lambda: _("Juniper Processor Utilization of Operating CPU"),
    )
)
