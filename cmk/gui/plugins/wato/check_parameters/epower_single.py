#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Integer, Tuple


def _parameter_valuespec_epower_single():
    return Tuple(
        help=_("Levels for the electrical power consumption of a device "),
        elements=[
            Integer(title=_("warning if at"), unit="Watt", default_value=300),
            Integer(title=_("critical if at"), unit="Watt", default_value=400),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="epower_single",
        group=RulespecGroupCheckParametersEnvironment,
        parameter_valuespec=_parameter_valuespec_epower_single,
        title=lambda: _("Electrical Power for Devices with only one phase"),
    )
)
