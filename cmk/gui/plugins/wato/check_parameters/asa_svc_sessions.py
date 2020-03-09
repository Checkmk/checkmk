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
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
)


def _parameter_valuespec_asa_svc_sessions():
    return Tuple(
        title=_("Number of active sessions"),
        help=_("This check monitors the current number of active sessions"),
        elements=[
            Integer(
                title=_("Warning at"),
                unit=_("sessions"),
                default_value=100,
            ),
            Integer(
                title=_("Critical at"),
                unit=_("sessions"),
                default_value=200,
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="asa_svc_sessions",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_asa_svc_sessions,
        title=lambda: _("Cisco SSl VPN Client Sessions"),
    ))
