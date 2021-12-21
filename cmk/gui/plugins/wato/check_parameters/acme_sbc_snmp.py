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


def _parameter_valuespec_acme_sbc_snmp():
    return Dictionary(
        elements=[
            (
                "levels_lower",
                Tuple(
                    title=_("Levels on health status score in percent"),
                    elements=[
                        Integer(title=_("Warning below"), unit=_("percent"), default_value=99),
                        Integer(title=_("Critical below"), unit=_("percent"), default_value=75),
                    ],
                ),
            ),
        ],
        required_keys=["levels_lower"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="acme_sbc_snmp",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_acme_sbc_snmp,
        title=lambda: _("ACME SBC health"),
    )
)
