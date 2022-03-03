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


def _parameter_valuespec_fortiauthenticator():
    return Dictionary(
        elements=[
            (
                "auth_fails",
                Tuple(
                    title=_("Authentication failures within the last 5 minutes"),
                    help=_(
                        "Define levels on the number of authentication failures within the last 5 minutes."
                    ),
                    elements=[
                        Integer(title=_("Warning at"), unit="failures", default_value=100),
                        Integer(title=_("Critical at"), unit="failures", default_value=200),
                    ],
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="fortiauthenticator_auth_fail",
        group=RulespecGroupCheckParametersNetworking,
        parameter_valuespec=_parameter_valuespec_fortiauthenticator,
        title=lambda: _("Fortinet FortiAuthenticator Authentication Failures"),
    )
)
