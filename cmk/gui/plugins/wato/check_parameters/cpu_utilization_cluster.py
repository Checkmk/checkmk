#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    ManualCheckParameterRulespec,
    rulespec_registry,
    RulespecGroupEnforcedServicesNetworking,
)
from cmk.gui.valuespec import Integer, ListOf, Percentage, Tuple

# NOTE: The rulesets in this file were deprecated in version 2.1.0i1


# TODO: Why is this only a manual check rulespec?
def _parameter_valuespec_cpu_utilization_cluster():
    return ListOf(
        valuespec=Tuple(
            elements=[
                Integer(title=_("Equal or more than"), unit=_("nodes")),
                Tuple(
                    elements=[
                        Percentage(title=_("Warning at a utilization of"), default_value=90.0),
                        Percentage(title=_("Critical at a utilization of"), default_value=95.0),
                    ],
                    title=_("Alert on too high CPU utilization"),
                ),
            ]
        ),
        help=_(
            "Configure levels for averaged CPU utilization depending on number of cluster nodes. "
            "The CPU utilization sums up the percentages of CPU time that is used "
            "for user processes and kernel routines over all available cores within "
            "the last check interval. The possible range is from 0% to 100%"
        ),
        title=_("Memory Usage"),
        add_label=_("Add limits"),
    )


rulespec_registry.register(
    ManualCheckParameterRulespec(
        check_group_name="cpu_utilization_cluster",
        group=RulespecGroupEnforcedServicesNetworking,
        parameter_valuespec=_parameter_valuespec_cpu_utilization_cluster,
        title=lambda: _("CPU Utilization of Clusters"),
        is_deprecated=True,
    )
)
