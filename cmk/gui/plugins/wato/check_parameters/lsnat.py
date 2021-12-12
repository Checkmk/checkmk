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
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_lsnat():
    return Dictionary(
        elements=[
            (
                "current_bindings",
                Tuple(
                    title=_("Number of current LSNAT bindings"),
                    elements=[
                        Integer(title=_("Warning at"), size=10, unit=_("bindings")),
                        Integer(title=_("Critical at"), size=10, unit=_("bindings")),
                    ],
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="lsnat",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_lsnat,
        title=lambda: _("Enterasys LSNAT Bindings"),
    )
)
