#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.kube import wrap_with_no_levels_dropdown
from cmk.gui.plugins.wato.check_parameters.memory_arbor import UsedSize
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import CascadingDropdown, Dictionary, Float, Percentage, Tuple


def valuespec_percentual(title: str) -> CascadingDropdown:
    return wrap_with_no_levels_dropdown(
        title=title,
        value_spec=Tuple(
            elements=[
                Percentage(title=_("Warning at"), default_value=80.0),
                Percentage(title=_("Critical at"), default_value=90.0),
            ]
        ),
    )


def _parameter_valuespec_memory():
    return Dictionary(
        help=_(
            "Here you can configure levels for usage, request "
            "utilization and limit utilization, respectively."
        ),
        title=_("Memory"),
        elements=[
            (
                "usage",
                wrap_with_no_levels_dropdown(
                    title=_("Upper levels for usage"), value_spec=UsedSize()
                ),
            ),
            (
                "request",
                valuespec_percentual(title=_("Upper levels for request utilization")),
            ),
            (
                "limit",
                valuespec_percentual(title=_("Upper levels for limit utilization")),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_memory",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_memory,
        title=lambda: _("Kubernetes memory resource utilization"),
    )
)


def _parameter_valuespec_cpu():
    return Dictionary(
        help=_(
            "Here you can configure levels for usage, request "
            "utilization and limit utilization, respectively."
        ),
        title=_("CPU"),
        elements=[
            (
                "usage",
                wrap_with_no_levels_dropdown(
                    title=_("Upper levels for usage"),
                    value_spec=Tuple(
                        elements=[
                            Float(title=_("Warning at"), default_value=0.5),
                            Float(title=_("Critical at"), default_value=1.0),
                        ]
                    ),
                ),
            ),
            (
                "request",
                valuespec_percentual(title=_("Upper levels for request utilization")),
            ),
            (
                "limit",
                valuespec_percentual(title=_("Upper levels for limit utilization")),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_cpu_usage",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_cpu,
        title=lambda: _("Kubernetes CPU resource utilization"),
    )
)
