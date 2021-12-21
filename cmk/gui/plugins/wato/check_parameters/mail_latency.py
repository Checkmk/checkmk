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
from cmk.gui.valuespec import Age, Tuple


def _parameter_valuespec_mail_latency():
    return Tuple(
        title=_("Upper levels for mail latency"),
        elements=[
            Age(title=_("Warning at"), default_value=40),
            Age(title=_("Critical at"), default_value=60),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="mail_latency",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_mail_latency,
        title=lambda: _("Mail latency"),
    )
)
