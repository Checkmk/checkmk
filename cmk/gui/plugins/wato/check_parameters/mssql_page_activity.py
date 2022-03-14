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
from cmk.gui.valuespec import Dictionary, Float, Tuple


def _parameter_valuespec_mssql_page_activity():
    return Dictionary(
        title=_("Page Activity Levels"),
        elements=[
            (
                "page_reads/sec",
                Tuple(
                    title=_("Reads/sec"),
                    elements=[
                        Float(title=_("warning at"), unit=_("/sec")),
                        Float(title=_("critical at"), unit=_("/sec")),
                    ],
                ),
            ),
            (
                "page_writes/sec",
                Tuple(
                    title=_("Writes/sec"),
                    elements=[
                        Float(title=_("warning at"), unit=_("/sec")),
                        Float(title=_("critical at"), unit=_("/sec")),
                    ],
                ),
            ),
            (
                "page_lookups/sec",
                Tuple(
                    title=_("Lookups/sec"),
                    elements=[
                        Float(title=_("warning at"), unit=_("/sec")),
                        Float(title=_("critical at"), unit=_("/sec")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_page_activity",
        group=RulespecGroupCheckParametersApplications,
        item_spec=mssql_item_spec_instance_tablespace,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mssql_page_activity,
        title=lambda: _("MSSQL Page Activity"),
    )
)
