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
from cmk.gui.valuespec import Integer, Tuple


def _parameter_valuespec_domino_users():
    return Tuple(
        title=_("Number of Lotus Domino Users"),
        elements=[
            Integer(title=_("warning at"), default_value=1000),
            Integer(title=_("critical at"), default_value=1500),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="domino_users",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_domino_users,
        title=lambda: _("Lotus Domino Users"),
    )
)
