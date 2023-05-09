#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Float,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_netscaler_dnsrates():
    return Dictionary(
        help=_("Counter rates of DNS parameters for Citrix Netscaler Loadbalancer "
               "Appliances"),
        elements=[
            (
                "query",
                Tuple(
                    title=_("Upper Levels for Total Number of DNS queries"),
                    elements=[
                        Float(title=_("Warning at"), default_value=1500.0, unit="/sec"),
                        Float(title=_("Critical at"), default_value=2000.0, unit="/sec")
                    ],
                ),
            ),
            (
                "answer",
                Tuple(
                    title=_("Upper Levels for Total Number of DNS replies"),
                    elements=[
                        Float(title=_("Warning at"), default_value=1500.0, unit="/sec"),
                        Float(title=_("Critical at"), default_value=2000.0, unit="/sec")
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="netscaler_dnsrates",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_netscaler_dnsrates,
        title=lambda: _("Citrix Netscaler DNS counter rates"),
    ))
