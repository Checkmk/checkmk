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
from cmk.gui.valuespec import Integer, Tuple


def _parameter_valuespec_logins():
    return Tuple(
        help=_("This rule defines upper limits for the number of logins on a system."),
        elements=[
            Integer(title=_("Warning at"), unit=_("users"), default_value=20),
            Integer(title=_("Critical at"), unit=_("users"), default_value=30),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="logins",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_logins,
        title=lambda: _("Number of Logins on System"),
    )
)
