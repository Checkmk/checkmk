#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _item_spec_siemens_plc_counter():
    return TextInput(
        title=_("Device Name and Value Ident"),
        help=_(
            "You need to concatenate the device name which is configured in the special agent "
            "for the PLC device separated by a space with the ident of the value which is also "
            "configured in the special agent."
        ),
    )


def _parameter_valuespec_siemens_plc_counter():
    return Dictionary(
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Counter level"),
                    elements=[
                        Integer(
                            title=_("Warning at"),
                        ),
                        Integer(
                            title=_("Critical at"),
                        ),
                    ],
                ),
            ),
        ],
        help=_(
            "This rule is used to configure thresholds for counter values read from "
            "Siemens PLC devices."
        ),
        title=_("Counter levels"),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="siemens_plc_counter",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_siemens_plc_counter,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_siemens_plc_counter,
        title=lambda: _("Siemens PLC Counter"),
    )
)
