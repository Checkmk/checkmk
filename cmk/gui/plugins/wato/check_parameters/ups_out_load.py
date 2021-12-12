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


def _item_spec_ups_out_load():
    return TextInput(
        title=_("Phase"), help=_("The identifier of the phase the power is related to.")
    )


def _parameter_valuespec_ups_out_load():
    return Dictionary(
        elements=[
            (
                "levels",
                Tuple(
                    elements=[
                        Integer(title=_("warning at"), unit="%", default_value=85),
                        Integer(title=_("critical at"), unit="%", default_value=90),
                    ],
                ),
            )
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ups_out_load",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_ups_out_load,
        parameter_valuespec=_parameter_valuespec_ups_out_load,
        title=lambda: _("Parameters for output loads of UPSs and PDUs"),
    )
)
