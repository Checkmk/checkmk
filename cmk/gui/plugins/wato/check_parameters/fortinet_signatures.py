#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Age, Alternative, Dictionary, FixedValue, Tuple


def _vs_fortinet_signatures(title):
    return Alternative(
        title=title,
        elements=[
            Tuple(
                title=_("Set levels"),
                elements=[
                    Age(title=_("Warning at"), default_value=86400),
                    Age(title=_("Critical at"), default_value=2 * 86400),
                ],
            ),
            Tuple(
                title=_("No levels"),
                elements=[
                    FixedValue(value=None, totext=""),
                    FixedValue(value=None, totext=""),
                ],
            ),
        ],
    )


def _parameter_valuespec_fortinet_signatures():
    return Dictionary(
        elements=[
            ("av_age", _vs_fortinet_signatures(_("Age of Anti-Virus signature"))),
            (
                "av_ext_age",
                _vs_fortinet_signatures(_("Age of Anti-Virus signature extended database")),
            ),
            ("ips_age", _vs_fortinet_signatures(_("Age of Intrusion Prevention signature"))),
            (
                "ips_ext_age",
                _vs_fortinet_signatures(
                    _("Age of Intrusion Prevention signature extended database")
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="fortinet_signatures",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fortinet_signatures,
        title=lambda: _("Fortigate Signatures"),
    )
)
