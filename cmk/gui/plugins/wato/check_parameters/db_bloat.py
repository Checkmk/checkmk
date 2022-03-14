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
from cmk.gui.valuespec import Dictionary, Filesize, Percentage, TextInput, Tuple


def _parameter_valuespec_db_bloat():
    return Dictionary(
        help=_(
            "This rule allows you to configure bloat levels for a databases tablespace and "
            "indexspace."
        ),
        elements=[
            (
                "table_bloat_abs",
                Tuple(
                    title=_("Table absolute bloat levels"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "table_bloat_perc",
                Tuple(
                    title=_("Table percentage bloat levels"),
                    help=_(
                        "Percentage in respect to the optimal utilization. "
                        "For example if an alarm should raise at 50% wasted space, you need "
                        "to configure 150%"
                    ),
                    elements=[
                        Percentage(title=_("Warning at"), maxvalue=None),
                        Percentage(title=_("Critical at"), maxvalue=None),
                    ],
                ),
            ),
            (
                "index_bloat_abs",
                Tuple(
                    title=_("Index absolute levels"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "index_bloat_perc",
                Tuple(
                    title=_("Index percentage bloat levels"),
                    help=_(
                        "Percentage in respect to the optimal utilization. "
                        "For example if an alarm should raise at 50% wasted space, you need "
                        "to configure 150%"
                    ),
                    elements=[
                        Percentage(title=_("Warning at"), maxvalue=None),
                        Percentage(title=_("Critical at"), maxvalue=None),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="db_bloat",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("Name of the database"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_db_bloat,
        title=lambda: _("PostgreSQL database bloat"),
    )
)
