#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Integer


def _parameter_valuespec_lsnat():
    return Dictionary(
        elements=[
            (
                "current_bindings",
                SimpleLevels(
                    title=_("Number of current LSNAT bindings"),
                    spec=Integer,
                    unit=_("bindings"),
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="lsnat",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_lsnat,
        title=lambda: _("Enterasys LSNAT Bindings"),
    )
)
