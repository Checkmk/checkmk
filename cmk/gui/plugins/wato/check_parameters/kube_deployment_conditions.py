#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
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
            "A deployment enters various states during its lifecycle. Depending on this a "
            "deployment may present different conditions. You can set a time for how long "
            "a condition is allowed to be in a certain state before the check alerts."
        ),
        elements=[
            (
                "progressing",
                age_levels_dropdown(_("Time until alert, if PROGRESSING condition is false")),
            ),
            (
                "available",
                age_levels_dropdown(_("Time until alert, if AVAILABLE condition is false")),
            ),
            (
                "replicafailure",
                age_levels_dropdown(_("Time until alert, if REPLICAFAILURE condition is true")),
            ),
        ],
        optional_keys=["progressing", "available", "replicafailure"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_deployment_conditions",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec,
        title=lambda: _("Kubernetes deployment conditions"),
    )
)
