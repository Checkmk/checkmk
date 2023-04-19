#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.cpu_utilization import cpu_util_elements
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersVirtualization,
)
from cmk.gui.valuespec import Dictionary


def _parameter_valuespec_prism_host_cpu():
    return Dictionary(
        help=_(
            "This rule configures levels for the CPU utilization (not load) for "
            "Nutanix host systems. "
            "The utilization percentage is computed with respect to the total "
            "number of CPUs. "
        ),
        elements=cpu_util_elements(),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="prism_host_cpu",
        group=RulespecGroupCheckParametersVirtualization,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_prism_host_cpu,
        title=lambda: _("Nutanix Host CPU utilization"),
    )
)
