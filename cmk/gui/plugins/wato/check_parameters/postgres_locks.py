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


def _parameter_valuespec_postgres_locks():
    return Dictionary(
        help=_(
            "This rule allows you to configure the limits for the SharedAccess and Exclusive Locks "
            "for a PostgreSQL database."
        ),
        elements=[
            (
                "levels_shared",
                Tuple(
                    title=_("Shared Access Locks"),
                    elements=[
                        Integer(title=_("Warning at"), minvalue=0),
                        Integer(title=_("Critical at"), minvalue=0),
                    ],
                ),
            ),
            (
                "levels_exclusive",
                Tuple(
                    title=_("Exclusive Locks"),
                    elements=[
                        Integer(title=_("Warning at"), minvalue=0),
                        Integer(title=_("Critical at"), minvalue=0),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="postgres_locks",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("Name of the database"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_postgres_locks,
        title=lambda: _("PostgreSQL Locks"),
    )
)
