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


def _parameter_valuespec_prism_cluster_cpu() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "util",
                Tuple(
                    elements=[
                        Percentage(title=_("Warning at a utilization of"), default_value=90.0),
                        Percentage(title=_("Critical at a utilization of"), default_value=95.0),
                    ],
                    title=_("Alert on excessive CPU utilization"),
                    help=_(
                        "This rule configures levels for the CPU utilization (not load) for "
                        "Nutanix cluster systems. "
                        "The utilization percentage is shown for the whole cluster."
                    ),
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="prism_cluster_cpu",
        group=RulespecGroupCheckParametersVirtualization,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_prism_cluster_cpu,
        title=lambda: _("Nutanix Cluster CPU utilization"),
    )
)
