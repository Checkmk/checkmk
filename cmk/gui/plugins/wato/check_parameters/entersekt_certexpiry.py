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


def _parameter_valuespec_entersekt_certexpiry():
    return Dictionary(
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Levels for number of days until expiration"),
                    elements=[
                        Integer(title=_("Warning if below"), default_value=20),
                        Integer(title=_("Critical if below"), default_value=10),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="entersekt_certexpiry",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_entersekt_certexpiry,
        title=lambda: _("Entersekt Certificate Expiration"),
    )
)
