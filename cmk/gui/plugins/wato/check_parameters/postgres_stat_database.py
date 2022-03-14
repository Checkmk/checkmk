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


def _parameter_valuespec_postgres_stat_database():
    return Dictionary(
        help=_(
            "This check monitors how often database objects in a PostgreSQL Database are accessed"
        ),
        elements=[
            (
                "blocks_read",
                Tuple(
                    title=_("Blocks read"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("blocks/s")),
                        Float(title=_("Critical at"), unit=_("blocks/s")),
                    ],
                ),
            ),
            (
                "xact_commit",
                Tuple(
                    title=_("Commits"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("/s")),
                        Float(title=_("Critical at"), unit=_("/s")),
                    ],
                ),
            ),
            (
                "tup_fetched",
                Tuple(
                    title=_("Fetches"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("/s")),
                        Float(title=_("Critical at"), unit=_("/s")),
                    ],
                ),
            ),
            (
                "tup_deleted",
                Tuple(
                    title=_("Deletes"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("/s")),
                        Float(title=_("Critical at"), unit=_("/s")),
                    ],
                ),
            ),
            (
                "tup_updated",
                Tuple(
                    title=_("Updates"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("/s")),
                        Float(title=_("Critical at"), unit=_("/s")),
                    ],
                ),
            ),
            (
                "tup_inserted",
                Tuple(
                    title=_("Inserts"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("/s")),
                        Float(title=_("Critical at"), unit=_("/s")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="postgres_stat_database",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Database name"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_postgres_stat_database,
        title=lambda: _("PostgreSQL Database Statistics"),
    )
)
