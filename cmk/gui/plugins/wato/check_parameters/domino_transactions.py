#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Integer,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_domino_transactions():
    return Tuple(
        title=_("Number of Transactions per Minute on a Lotus Domino Server"),
        elements=[
            Integer(title=_("warning at"), default_value=30000),
            Integer(title=_("critical at"), default_value=35000),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="domino_transactions",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_domino_transactions,
        title=lambda: _("Lotus Domino Transactions"),
    ))
