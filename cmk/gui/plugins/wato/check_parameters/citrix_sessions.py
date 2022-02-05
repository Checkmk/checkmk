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


def _parameter_valuespec_citrix_sessions():
    return Dictionary(
        elements=[
            (
                "total",
                Tuple(
                    title=_("Total number of Sessions"),
                    elements=[
                        Integer(title=_("warning at"), unit="Sessions"),
                        Integer(title=_("critical at"), unit="Session"),
                    ],
                ),
            ),
            (
                "active",
                Tuple(
                    title=_("Number of Active Sessions"),
                    elements=[
                        Integer(title=_("warning at"), unit="Sessions"),
                        Integer(title=_("critical at"), unit="Session"),
                    ],
                ),
            ),
            (
                "inactive",
                Tuple(
                    title=_("Number of Inactive Sessions"),
                    elements=[
                        Integer(title=_("warning at"), unit="Sessions"),
                        Integer(title=_("critical at"), unit="Session"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="citrix_sessions",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_citrix_sessions,
        title=lambda: _("Citrix Terminal Server Sessions"),
    )
)
