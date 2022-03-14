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


def _parameter_valuespec_mssql_connections():
    return Dictionary(
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Upper levels for the number of active database connections"),
                    elements=[
                        Integer(title=_("Warning if over"), default_value=20),
                        Integer(title=_("Critical if over"), default_value=50),
                    ],
                ),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_connections",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Database identifier"), allow_empty=True),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mssql_connections,
        title=lambda: _("MSSQL Connections"),
    )
)
