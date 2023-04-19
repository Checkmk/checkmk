#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
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
        elements=[
            (
                "pending",
                age_levels_dropdown(
                    _("Time until alert, if latest CronJob job is in pending state")
                ),
            ),
            (
                "running",
                age_levels_dropdown(
                    _(
                        "Time until alert, if the latest CronJob job has been running for "
                        "longer than set time"
                    )
                ),
            ),
        ],
        optional_keys=["pending", "running"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_cronjob_status",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec,
        title=lambda: _("Kubernetes CronJob status"),
    )
)
