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
from cmk.gui.valuespec import Dictionary, Float, Integer, Tuple


def _parameter_valuespec_prism_cluster_io() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "io",
                Tuple(
                    elements=[
                        Float(title=_("Warning at"), unit=_("MB/s"), default_value=500.0),
                        Float(title=_("Critical at"), unit=_("MB/s"), default_value=1000.0),
                    ],
                    title=_("Levels for IO traffic per second."),
                ),
            ),
            (
                "iops",
                Tuple(
                    elements=[
                        Integer(title=_("Warning at"), unit=_("iops"), default_value=10000),
                        Integer(title=_("Critical at"), unit=_("iops"), default_value=20000),
                    ],
                    title=_("Levels for IO operations per second."),
                ),
            ),
            (
                "iolat",
                Tuple(
                    elements=[
                        Float(title=_("Warning at"), unit=_("ms"), default_value=500.0),
                        Float(title=_("Critical at"), unit=_("ms"), default_value=1000.0),
                    ],
                    title=_("Levels for IO latency."),
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="prism_cluster_io",
        group=RulespecGroupCheckParametersVirtualization,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_prism_cluster_io,
        title=lambda: _("Nutanix Cluster IO utilization"),
    )
)
