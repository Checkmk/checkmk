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


def _parameter_valuespec_netscaler_sslcerts():
    return Dictionary(
        elements=[
            (
                "age_levels",
                Tuple(
                    title=_("Remaining days of validity"),
                    elements=[
                        Integer(
                            title=_("Warning below"),
                            default_value=30,
                            minvalue=0,
                        ),
                        Integer(
                            title=_("Critical below"),
                            default_value=10,
                            minvalue=0,
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="netscaler_sslcerts",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("Name of Certificate"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_netscaler_sslcerts,
        title=lambda: _("Citrix Netscaler SSL certificates"),
    )
)
