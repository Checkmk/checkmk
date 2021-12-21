#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def __levels(title):
    return Tuple(
        title=title,
        elements=[
            Integer(title=_("Warning above"), unit=_("seconds")),
            Integer(title=_("Critical above"), unit=_("seconds")),
        ],
    )


def _parameter_valuespec():
    return Dictionary(
        help=_(
            (
                "A pod's status depends on an array of PodConditions through which the"
                " Pod has or has not yet passed. This rule allows you to define tolerating"
                " time periods for each of those conditions."
            )
        ),
        elements=[
            (
                "initialized",
                __levels(_("Define a tolerating time period for non-initialized condition.")),
            ),
            (
                "scheduled",
                __levels(
                    _("Define a tolerating time period for non-scheduled condition."),
                ),
            ),
            (
                "containersready",
                __levels(
                    _(
                        "Define a tolerating time period for pod's containers not in ready condition."
                    ),
                ),
            ),
            (
                "ready",
                __levels(
                    _("Define a tolerating time period for non-ready condition."),
                ),
            ),
        ],
        optional_keys=["initialized", "scheduled", "containersready", "ready"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="k8s_pod_conditions",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec,
        title=lambda: _("Pod conditions"),
    )
)
