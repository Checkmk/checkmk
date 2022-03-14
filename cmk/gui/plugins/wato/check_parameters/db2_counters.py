#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Float, TextInput, Tuple


def _item_spec_db2_counters():
    return TextInput(
        title=_("Instance"), help=_("DB2 instance followed by database name, e.g db2taddm:CMDBS1")
    )


def _parameter_valuespec_db2_counters():
    return Dictionary(
        help=_(
            "This rule allows you to configure limits for the deadlocks and lockwaits "
            "counters of a DB2."
        ),
        elements=[
            (
                "deadlocks",
                Tuple(
                    title=_("Deadlocks"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("deadlocks/sec")),
                        Float(title=_("Critical at"), unit=_("deadlocks/sec")),
                    ],
                ),
            ),
            (
                "lockwaits",
                Tuple(
                    title=_("Lockwaits"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("lockwaits/sec")),
                        Float(title=_("Critical at"), unit=_("lockwaits/sec")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="db2_counters",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_db2_counters,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_db2_counters,
        title=lambda: _("DB2 Counters"),
    )
)
