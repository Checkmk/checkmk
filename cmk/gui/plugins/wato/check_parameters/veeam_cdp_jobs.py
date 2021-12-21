#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Age, Dictionary, TextInput, Tuple


def _parameter_valuespec_veeam_cdp():
    return Dictionary(
        elements=[
            (
                "age",
                Tuple(
                    title=_("Time since last CDP run"),
                    elements=[
                        Age(title=_("Warning if older than"), default_value=108000),
                        Age(title=_("Critical if older than"), default_value=172800),
                    ],
                ),
            )
        ],
        required_keys=["age"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="veeam_cdp_jobs",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Job name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_veeam_cdp,
        title=lambda: _("Veeam: Time since last CDP run"),
    )
)
