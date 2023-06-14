#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersVirtualization,
)
from cmk.gui.valuespec import Dictionary, Percentage, Tuple


def _parameter_valuespec_prism_vm_memory():
    return Dictionary(
        elements=[
            (
                "levels_upper",
                Tuple(
                    title=_("Specify levels in percentage of total RAM"),
                    elements=[
                        Percentage(title=_("Warning at a RAM usage of"), default_value=80.0),
                        Percentage(title=_("Critical at a RAM usage of"), default_value=90.0),
                    ],
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="prism_vm_memory",
        group=RulespecGroupCheckParametersVirtualization,
        parameter_valuespec=_parameter_valuespec_prism_vm_memory,
        title=lambda: _("Nutanix VM memory usage"),
    )
)
