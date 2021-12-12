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
from cmk.gui.valuespec import Integer, TextInput, Tuple


def _item_spec_apc_power():
    return TextInput(
        title=_("Phase"),
        help=_("The identifier of the phase the power is related to."),
    )


def _parameter_valuespec_apc_power():
    return Tuple(
        title=_("Power Comsumption of APC Devices"),
        elements=[
            Integer(
                title=_("Warning below"),
                unit=_("W"),
                default_value=20,
            ),
            Integer(
                title=_("Critical below"),
                unit=_("W"),
                default_value=1,
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="apc_power",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_apc_power,
        parameter_valuespec=_parameter_valuespec_apc_power,
        title=lambda: _("APC Power Consumption"),
    )
)
