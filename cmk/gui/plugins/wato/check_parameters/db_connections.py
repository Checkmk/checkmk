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
from cmk.gui.valuespec import Dictionary, Integer, Percentage, TextInput, Transform, Tuple


def _transform_connection_type(params):
    # The old WATO rule did not differentiate between "active" and "idle"
    # The old levels were refering to the "active" type
    for metric_type in ("perc", "abs"):
        if "levels_%s" % metric_type in params.keys():
            params["levels_%s_active" % metric_type] = params["levels_%s" % metric_type]
            params.pop("levels_%s" % metric_type)

    return params


def _parameter_valuespec_db_connections():
    return Transform(
        valuespec=Dictionary(
            help=_(
                "This rule allows you to configure the number of maximum concurrent "
                "connections for a given database."
            ),
            elements=[
                (
                    "levels_perc_active",
                    Tuple(
                        title=_("Percentage of maximum available active connections"),
                        elements=[
                            Percentage(
                                title=_("Warning at"),
                                # xgettext: no-python-format
                                unit=_("% of maximum active connections"),
                            ),
                            Percentage(
                                title=_("Critical at"),
                                # xgettext: no-python-format
                                unit=_("% of maximum active connections"),
                            ),
                        ],
                    ),
                ),
                (
                    "levels_abs_active",
                    Tuple(
                        title=_("Absolute number of active connections"),
                        elements=[
                            Integer(title=_("Warning at"), minvalue=0, unit=_("connections")),
                            Integer(title=_("Critical at"), minvalue=0, unit=_("connections")),
                        ],
                    ),
                ),
                (
                    "levels_perc_idle",
                    Tuple(
                        title=_("Percentage of maximum available idle connections"),
                        elements=[
                            Percentage(
                                title=_("Warning at"),
                                # xgettext: no-python-format
                                unit=_("% of maximum idle connections"),
                            ),
                            Percentage(
                                title=_("Critical at"),
                                # xgettext: no-python-format
                                unit=_("% of maximum idle connections"),
                            ),
                        ],
                    ),
                ),
                (
                    "levels_abs_idle",
                    Tuple(
                        title=_("Absolute number of idle connections"),
                        elements=[
                            Integer(title=_("Warning at"), minvalue=0, unit=_("idle connections")),
                            Integer(title=_("Critical at"), minvalue=0, unit=_("idle connections")),
                        ],
                    ),
                ),
            ],
        ),
        forth=_transform_connection_type,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="db_connections",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("Name of the database"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_db_connections,
        title=lambda: _("PostgreSQL database connections"),
    )
)


def _parameter_valuespec_db_connections_mongodb():
    return Dictionary(
        help=_(
            "This rule allows you to configure the number of incoming connections from clients "
            "to the database server."
        ),
        elements=[
            (
                "levels_perc",
                Tuple(
                    title=_("Percentage of maximum available connections"),
                    elements=[
                        Percentage(
                            title=_("Warning at"),
                            # xgettext: no-python-format
                            unit=_("% of maximum connections"),
                        ),
                        Percentage(
                            title=_("Critical at"),
                            # xgettext: no-python-format
                            unit=_("% of maximum connections"),
                        ),
                    ],
                ),
            ),
            (
                "levels_abs",
                Tuple(
                    title=_("Absolute number of incoming connections"),
                    elements=[
                        Integer(title=_("Warning at"), minvalue=0, unit=_("connections")),
                        Integer(title=_("Critical at"), minvalue=0, unit=_("connections")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="db_connections_mongodb",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("Name of the database"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_db_connections_mongodb,
        title=lambda: _("MongoDB database connections"),
    )
)
