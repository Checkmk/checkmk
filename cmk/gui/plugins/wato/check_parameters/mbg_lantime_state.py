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


def _parameter_valuespec_mbg_lantime_state():
    return Dictionary(
        title=_("Meinberg Lantime State"),
        elements=[
            (
                "stratum",
                Tuple(
                    title=_("Warning levels for Stratum"),
                    elements=[
                        Integer(
                            title=_("Warning at"),
                            default_value=2,
                        ),
                        Integer(
                            title=_("Critical at"),
                            default_value=3,
                        ),
                    ],
                ),
            ),
            (
                "offset",
                Tuple(
                    title=_("Warning levels for Time Offset"),
                    elements=[
                        Integer(
                            title=_("Warning at"),
                            unit=_("microseconds"),
                            default_value=10,
                        ),
                        Integer(
                            title=_("Critical at"),
                            unit=_("microseconds"),
                            default_value=20,
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="mbg_lantime_state",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mbg_lantime_state,
        title=lambda: _("Meinberg Lantime State"),
    )
)
