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
from cmk.gui.valuespec import Age, Alternative, Dictionary, FixedValue, TextInput, Tuple


def _parameter_valuespec_postgres_maintenance():
    return Dictionary(
        help=_(
            "With this rule you can set limits for the VACUUM and ANALYZE operation of "
            "a PostgreSQL database. Keep in mind that each table within a database is checked "
            "with this limits."
        ),
        elements=[
            (
                "last_vacuum",
                Tuple(
                    title=_("Time since the last VACUUM"),
                    elements=[
                        Age(title=_("Warning if older than"), default_value=86400 * 7),
                        Age(title=_("Critical if older than"), default_value=86400 * 14),
                    ],
                ),
            ),
            (
                "last_analyze",
                Tuple(
                    title=_("Time since the last ANALYZE"),
                    elements=[
                        Age(title=_("Warning if older than"), default_value=86400 * 7),
                        Age(title=_("Critical if older than"), default_value=86400 * 14),
                    ],
                ),
            ),
            (
                "never_analyze_vacuum",
                Alternative(
                    title=_("Never analyzed/vacuumed tables"),
                    elements=[
                        Tuple(
                            title=_("Age of never analyzed/vacuumed tables"),
                            elements=[
                                Age(title=_("Warning if older than"), default_value=0),
                                Age(
                                    title=_("Critical if older than"),
                                    default_value=1000 * 365 * 24 * 3600,
                                ),
                            ],
                        ),
                        FixedValue(
                            value=None,
                            title=_("Do not check age of never analyzed/vacuumed tables"),
                            totext="",
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="postgres_maintenance",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("Name of the database"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_postgres_maintenance,
        title=lambda: _("PostgreSQL VACUUM and ANALYZE"),
    )
)
