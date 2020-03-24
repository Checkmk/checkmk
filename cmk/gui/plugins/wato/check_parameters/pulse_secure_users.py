#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Integer,
    Tuple,
)

from cmk.gui.plugins.wato import (CheckParameterRulespecWithoutItem, rulespec_registry,
                                  RulespecGroupCheckParametersApplications)


def _parameter_valuespec_pulse_secure_users():
    return Tuple(
        title=_("Number of signed-in web users"),
        elements=[
            Integer(title=_("warning at")),
            Integer(title=_("critical at")),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="pulse_secure_users",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_pulse_secure_users,
        title=lambda: _("Pulse Secure users"),
    ))
