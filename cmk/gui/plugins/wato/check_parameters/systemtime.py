#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Age, Dictionary, Transform, Tuple


def _parameter_valuespec_systemtime():
    return Transform(
        valuespec=Dictionary(
            title="Time offset",
            elements=[
                (
                    "levels",
                    Tuple(
                        title=_("Levels on time offset"),
                        elements=[
                            Age(title=_("Warning at"), default_value=30),
                            Age(title=_("Critical at"), default_value=60),
                        ],
                    ),
                ),
            ],
            optional_keys=False,
        ),
        forth=lambda v: {"levels": v} if isinstance(v, tuple) else v,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="systemtime",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_systemtime,
        title=lambda: _("Windows system time offset"),
    )
)
