#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.kube import age_levels_dropdown
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary


def _parameter_valuespec():
    return Dictionary(
        help=_(
            (
                "A pod's status depends on an array of conditions through which the"
                " Pod has or has not yet passed. You can set a time for how long a condition"
                " is allowed to be in a failed state before the check alerts."
            )
        ),
        elements=[
            ("scheduled", age_levels_dropdown(_("Time until alert, if pod not scheduled"))),
            ("initialized", age_levels_dropdown(_("Time until alert, if pod not initialized"))),
            (
                "containersready",
                age_levels_dropdown(_("Time until alert, if pod's containers not ready")),
            ),
            ("ready", age_levels_dropdown(_("Time until alert, if pod not ready"))),
        ],
        optional_keys=["initialized", "scheduled", "containersready", "ready"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_pod_conditions",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec,
        title=lambda: _("Kubernetes pod conditions"),
    )
)
