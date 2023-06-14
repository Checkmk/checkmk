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


def _parameter_valuespec_prism_vm_cpu():
    return Dictionary(
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Specify levels in percentage of CPU usage"),
                    elements=[
                        Percentage(title=_("Warning at"), unit=_("%")),
                        Percentage(title=_("Critical at"), unit=_("%")),
                    ],
                ),
            ),
            (
                "levels_rdy",
                Tuple(
                    title=_("Specify levels if percentage of CPU ready state"),
                    elements=[
                        Percentage(title=_("Warning at"), unit=_("%")),
                        Percentage(title=_("Critical at"), unit=_("%")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="prism_vm_cpu",
        group=RulespecGroupCheckParametersVirtualization,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_prism_vm_cpu,
        title=lambda: _("Nutanix VM CPU utilization"),
    )
)
