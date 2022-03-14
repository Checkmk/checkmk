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


def _item_spec_nginx_status():
    return TextInput(
        title=_("Nginx Server"),
        help=_("A string-combination of servername and port, e.g. 127.0.0.1:80."),
    )


def _parameter_valuespec_nginx_status():
    return Dictionary(
        elements=[
            (
                "active_connections",
                Tuple(
                    title=_("Active Connections"),
                    help=_(
                        "You can configure upper thresholds for the currently active "
                        "connections handled by the web server."
                    ),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("connections")),
                        Integer(title=_("Critical at"), unit=_("connections")),
                    ],
                ),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="nginx_status",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_nginx_status,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_nginx_status,
        title=lambda: _("Nginx Status"),
    )
)
