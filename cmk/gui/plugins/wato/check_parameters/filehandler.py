#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, Percentage, Tuple


def _parameter_valuespec_filehandler():
    return Dictionary(
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Levels"),
                    default_value=(80.0, 90.0),
                    elements=[
                        Percentage(title=_("Warning at"), unit=_("%")),
                        Percentage(title=_("Critical at"), unit=_("%")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="filehandler",
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_filehandler,
        title=lambda: _("Filehandler"),
    )
)
