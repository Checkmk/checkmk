#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_netscaler_tcp_conns():
    return Dictionary(
        elements=[
            (
                "client_conns",
                Tuple(
                    title=_("Max. number of client connections"),
                    elements=[
                        Integer(
                            title=_("Warning at"),
                            default_value=25000,
                        ),
                        Integer(
                            title=_("Critical at"),
                            default_value=30000,
                        ),
                    ],
                ),
            ),
            (
                "server_conns",
                Tuple(
                    title=_("Max. number of server connections"),
                    elements=[
                        Integer(
                            title=_("Warning at"),
                            default_value=25000,
                        ),
                        Integer(
                            title=_("Critical at"),
                            default_value=30000,
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="netscaler_tcp_conns",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_netscaler_tcp_conns,
        title=lambda: _("Citrix Netscaler Loadbalancer TCP Connections"),
    )
)
