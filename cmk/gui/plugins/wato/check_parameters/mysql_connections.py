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
from cmk.gui.valuespec import Dictionary, Percentage, TextInput, Tuple


def _item_spec_mysql_connections():
    return TextInput(
        title=_("Instance"),
        default_value="mysql",
        help=_("Only needed if you have multiple MySQL Instances on one server"),
    )


def _parameter_valuespec_mysql_connections():
    return Dictionary(
        elements=[
            (
                "perc_used",
                Tuple(
                    title=_("Max. parallel connections"),
                    help=_(
                        "Compares the maximum number of connections that have been "
                        "in use simultaneously since the server started with the maximum simultaneous "
                        "connections allowed by the configuration of the server. This threshold "
                        "raises warning/critical states if the percentage is equal to "
                        "or above the configured levels."
                    ),
                    elements=[
                        Percentage(title=_("Warning at")),
                        Percentage(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "perc_conn_threads",
                Tuple(
                    title=("Currently open connections"),
                    help=_(
                        "Compares the number of currently open connections to the server "
                        "with the maximum simultaneous connections allowed by the configuration "
                        "of the server. This threshold raises warning/critical states if the "
                        "percentage is equal to or above the configured levels."
                    ),
                    elements=[
                        Percentage(title=_("Warning at")),
                        Percentage(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mysql_connections",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_mysql_connections,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mysql_connections,
        title=lambda: _("MySQL Connections"),
    )
)
