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


def _parameter_valuespec_mssql_stats():
    return Dictionary(
        elements=[
            (
                "batch_requests/sec",
                Tuple(
                    title=_("Batch Requests/sec"),
                    elements=[
                        Float(title=_("warning at"), unit=_("/sec"), default_value=100000.0),
                        Float(title=_("critical at"), unit=_("/sec"), default_value=200000.0),
                    ],
                ),
            ),
            (
                "sql_compilations/sec",
                Tuple(
                    title=_("SQL Compilations/sec"),
                    elements=[
                        Float(title=_("warning at"), unit=_("/sec"), default_value=10000.0),
                        Float(title=_("critical at"), unit=_("/sec"), default_value=20000.0),
                    ],
                ),
            ),
            (
                "sql_re-compilations/sec",
                Tuple(
                    title=_("SQL Re-Compilations/sec"),
                    elements=[
                        Float(title=_("warning at"), unit=_("/sec"), default_value=10000.0),
                        Float(title=_("critical at"), unit=_("/sec"), default_value=200.0),
                    ],
                ),
            ),
            (
                "locks_per_batch",
                Tuple(
                    title=_("Locks/Batch"),
                    elements=[
                        Float(title=_("warning at"), default_value=1000.0),
                        Float(title=_("critical at"), default_value=3000.0),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_stats",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("Counter ID"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mssql_stats,
        title=lambda: _("MSSQL Statistics"),
    )
)
