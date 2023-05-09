#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Integer,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_oracle_longactivesessions():
    return Dictionary(elements=[("levels",
                                 Tuple(
                                     title=_("Levels of active sessions"),
                                     elements=[
                                         Integer(title=_("Warning if more than"),
                                                 unit=_("sessions")),
                                         Integer(title=_("Critical if more than"),
                                                 unit=_("sessions")),
                                     ],
                                 ))],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="oracle_longactivesessions",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Database SID"), size=12, allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_oracle_longactivesessions,
        title=lambda: _("Oracle Long Active Sessions"),
    ))
