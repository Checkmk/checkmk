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
from cmk.gui.valuespec import Dictionary, Float, Integer, TextInput, Tuple


def _item_spec_sap_dialog():
    return TextInput(
        title=_("System ID"),
        help=_("The SAP system ID."),
    )


def _parameter_valuespec_sap_dialog():
    return Dictionary(
        elements=[
            (
                "UsersLoggedIn",
                Tuple(
                    title=_("Number of Loggedin Users"),
                    elements=[
                        Integer(title=_("Warning at"), label=_("Users")),
                        Integer(title=_("Critical at"), label=_("Users")),
                    ],
                ),
            ),
            (
                "FrontEndNetTime",
                Tuple(
                    title=_("Frontend net time"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("ms")),
                        Float(title=_("Critical at"), unit=_("ms")),
                    ],
                ),
            ),
            (
                "ResponseTime",
                Tuple(
                    title=_("Response Time"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("ms")),
                        Float(title=_("Critical at"), unit=_("ms")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="sap_dialog",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_sap_dialog,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_sap_dialog,
        title=lambda: _("SAP Dialog"),
    )
)
