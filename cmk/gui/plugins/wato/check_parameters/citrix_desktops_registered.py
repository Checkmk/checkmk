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


def _parameter_valuespec_plug_count():
    return Dictionary(
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Upper levels for the number of registered desktops"),
                    elements=[
                        Integer(title=_("warning if at")),
                        Integer(title=_("critical if at")),
                    ],
                ),
            ),
            (
                "levels_lower",
                Tuple(
                    title=_("Lower levels for the number of registered desktops"),
                    elements=[
                        Integer(title=_("warning if below")),
                        Integer(title=_("critical if below")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="citrix_desktops_registered",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_plug_count,
        title=lambda: _("Citrix Desktops Registered"),
    )
)
