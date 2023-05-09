#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Integer,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_skype_mobile():
    return Dictionary(
        elements=[('requests_processing',
                   Dictionary(
                       title=_("Requests in Processing"),
                       elements=[
                           ("upper",
                            Tuple(elements=[
                                Integer(title=_("Warning at"),
                                        unit=_("per second"),
                                        default_value=10000),
                                Integer(title=_("Critical at"),
                                        unit=_("per second"),
                                        default_value=20000),
                            ],)),
                       ],
                       optional_keys=[],
                   ))],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="skype_mobile",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_skype_mobile,
        title=lambda: _("Skype for Business Mobile"),
    ))
