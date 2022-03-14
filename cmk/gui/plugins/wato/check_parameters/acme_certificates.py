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
from cmk.gui.valuespec import Age, Dictionary, TextInput, Tuple


def _item_spec_acme_certificates():
    return TextInput(
        title=_("Name of certificate"),
        allow_empty=False,
    )


def _parameter_valuespec_acme_certificates():
    return Dictionary(
        elements=[
            (
                "expire_lower",
                Tuple(
                    title=_("Lower age levels for expire date"),
                    elements=[
                        Age(title=_("Warning if below"), default_value=604800),
                        Age(title=_("Critical if below"), default_value=2592000),
                    ],
                ),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="acme_certificates",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_acme_certificates,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_acme_certificates,
        title=lambda: _("ACME certificates"),
    )
)
