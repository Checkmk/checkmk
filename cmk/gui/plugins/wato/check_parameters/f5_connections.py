#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_f5_connections():
    return Dictionary(
        elements=[
            (
                "conns",
                Levels(
                    title=_("Max. number of connections"),
                    default_value=None,
                    default_levels=(25000, 30000),
                ),
            ),
            (
                "ssl_conns",
                Levels(
                    title=_("Max. number of SSL connections"),
                    default_value=None,
                    default_levels=(25000, 30000),
                ),
            ),
            (
                "connections_rate",
                Levels(
                    title=_("Maximum connections per second"),
                    default_value=None,
                    default_levels=(500, 1000),
                ),
            ),
            (
                "connections_rate_lower",
                Tuple(
                    title=_("Minimum connections per second"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "http_req_rate",
                Levels(
                    title=_("HTTP requests per second"),
                    default_value=None,
                    default_levels=(500, 1000),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="f5_connections",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_f5_connections,
        title=lambda: _("F5 Loadbalancer Connections"),
    )
)
