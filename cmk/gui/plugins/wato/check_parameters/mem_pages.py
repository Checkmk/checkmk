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
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_mem_pages():
    return Dictionary(
        elements=[
            (
                "pages_per_second",
                Tuple(
                    title=_("Pages per second"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("pages/s")),
                        Integer(title=_("Critical at"), unit=_("pages/s")),
                    ],
                ),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="mem_pages",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mem_pages,
        title=lambda: _("Memory Pages Statistics"),
    )
)
