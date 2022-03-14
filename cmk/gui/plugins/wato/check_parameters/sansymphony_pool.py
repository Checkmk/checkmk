#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Integer, TextInput, Tuple


def _parameter_valuespec_sansymphony_pool():
    return Tuple(
        help=_("This rule sets the warn and crit levels for the percentage of allocated pools"),
        elements=[
            Integer(
                title=_("Warning at"),
                unit=_("percent"),
                default_value=80,
            ),
            Integer(
                title=_("Critical at"),
                unit=_("percent"),
                default_value=90,
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="sansymphony_pool",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("Name of the pool"),
        ),
        parameter_valuespec=_parameter_valuespec_sansymphony_pool,
        title=lambda: _("Sansymphony pool allocation"),
    )
)
