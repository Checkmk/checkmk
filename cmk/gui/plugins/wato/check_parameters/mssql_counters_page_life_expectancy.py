#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.utils import mssql_item_spec_instance_tablespace
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Age, Dictionary, Tuple


def _parameter_valuespec_mssql_counters_ple():
    return Dictionary(
        help=_("This check monitors MSSQL page life expectancies."),
        elements=[
            (
                "mssql_min_page_life_expectancy",
                Tuple(
                    title=_("Minimum Page Life Expectancy"),
                    elements=[
                        Age(title=_("Warning below")),
                        Age(title=_("Critical below")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_counters_page_life_expectancy",
        group=RulespecGroupCheckParametersApplications,
        item_spec=mssql_item_spec_instance_tablespace,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mssql_counters_ple,
        title=lambda: _("MSSQL Page Life Expectancy"),
    )
)
