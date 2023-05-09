#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Tuple,
    Integer,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)


def _parameter_valuespec_palo_alto_sessions():
    return Dictionary(elements=[
        ("levels_sessions_used",
         Tuple(
             title=_("Levels for sessions used"),
             elements=[
                 Integer(title=_("Warning at"), default_value=60, unit=u"%"),
                 Integer(title=_("Critical at"), default_value=70, unit=u"%"),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="palo_alto_sessions",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_palo_alto_sessions,
        title=lambda: _("Palo Alto Active Sessions"),
    ))
