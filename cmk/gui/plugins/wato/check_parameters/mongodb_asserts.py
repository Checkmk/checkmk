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
from cmk.gui.valuespec import Dictionary, Float, Tuple


def _parameter_valuespec_mongodb_asserts():
    return Dictionary(
        elements=[
            (
                "%s_assert_rate" % what,
                Tuple(
                    title=_("%s rate") % what.title(),
                    elements=[
                        Float(title=_("Warning at"), unit=_("Asserts / s"), default_value=1.0),
                        Float(title=_("Critical at"), unit=_("Asserts / s"), default_value=2.0),
                    ],
                ),
            )
            for what in ["msg", "rollovers", "regular", "warning", "user"]
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="mongodb_asserts",
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mongodb_asserts,
        title=lambda: _("MongoDB Assert Rates"),
    )
)
