#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import Tuple, Integer

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)


def fortigate_sessions_element() -> Tuple:
    return Tuple(
        title=_("Levels for active sessions"),
        elements=[
            Integer(title=_("Warning at"), default_value=100000, size=10),
            Integer(title=_("Critical at"), default_value=150000, size=10),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="fortigate_sessions",
        group=RulespecGroupCheckParametersNetworking,
        parameter_valuespec=fortigate_sessions_element,
        title=lambda: _("Fortigate Active Sessions"),
    ))
