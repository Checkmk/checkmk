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


def _parameter_valuespec_fireeye_lic():
    return Dictionary(
        elements=[
            (
                "days",
                Tuple(
                    title=_("Levels for Fireeye License Expiration"),
                    elements=[
                        Integer(title="Warning at", default_value=90, unit="days"),
                        Integer(title="Critical at", default_value=120, unit="days"),
                    ],
                ),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fireeye_lic",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("License Feature")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fireeye_lic,
        title=lambda: _("Fireeye Licenses"),
    )
)
