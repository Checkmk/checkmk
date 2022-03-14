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
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _item_spec_db2_connections():
    return TextInput(
        title=_("Instance"), help=_("DB2 instance followed by database name, e.g db2taddm:CMDBS1")
    )


def _parameter_valuespec_db2_connections():
    return Dictionary(
        help=_("This rule allows you to set limits for the maximum number of DB2 connections"),
        elements=[
            (
                "levels_total",
                Tuple(
                    title=_("Number of current connections"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("connections"), default_value=150),
                        Integer(title=_("Critical at"), unit=_("connections"), default_value=200),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="db2_connections",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_db2_connections,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_db2_connections,
        title=lambda: _("DB2 Connections"),
    )
)
