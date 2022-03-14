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
from cmk.gui.valuespec import Float, TextInput, Tuple


def _parameter_valuespec_ocprot_current():
    return Tuple(
        elements=[
            Float(title=_("Warning at"), unit="A", default_value=14.0),
            Float(title=_("Critical at"), unit="A", default_value=15.0),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ocprot_current",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=lambda: TextInput(title=_("The Index of the Overcurrent Protector")),
        parameter_valuespec=_parameter_valuespec_ocprot_current,
        title=lambda: _("Electrical Current of Overcurrent Protectors"),
    )
)
