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
from cmk.gui.valuespec import Dictionary, Integer, Percentage, Transform, Tuple


def _parameter_valuespec_threads():
    return Transform(
        Dictionary(
            elements=[
                (
                    "levels",
                    Tuple(
                        title=_("Absolute levels"),
                        elements=[
                            Integer(title=_("Warning at"), unit=_("threads"), default_value=2000),
                            Integer(title=_("Critical at"), unit=_("threads"), default_value=4000),
                        ],
                    ),
                ),
                (
                    "levels_percent",
                    Tuple(
                        title=_("Relative levels"),
                        elements=[
                            Percentage(title=_("Warning at"), default_value=80),
                            Percentage(title=_("Critical at"), default_value=90),
                        ],
                    ),
                ),
            ],
        ),
        forth=lambda params: params if isinstance(params, dict) else {"levels": params},
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="threads",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_threads,
        title=lambda: _("Number of threads"),
    )
)
