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


def _item_spec_netapp_systemtime():
    return TextInput(
        title=_("Name of the node"),
        allow_empty=False,
    )


def _parameter_valuespec_netapp_systemtime():
    return Dictionary(
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Set upper levels for the time difference"),
                    help=_(
                        "Here you can Set upper levels for the time difference "
                        "between agent and system time."
                    ),
                    elements=[
                        Age(title=_("Warning if at")),
                        Age(title=_("Critical if at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="netapp_systemtime",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_netapp_systemtime,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_netapp_systemtime,
        title=lambda: _("Netapp systemtime"),
    )
)
