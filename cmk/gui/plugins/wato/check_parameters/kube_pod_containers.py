#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput


def _parameter_valuespec():
    return Dictionary(
        elements=[
            (
                "failed_state",
                MonitoringState(
                    title=_(
                        (
                            "Monitoring state if a container terminates "
                            "unsuccessfully (non-zero exit code)"
                        )
                    ),
                    default_value=2,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="kube_pod_containers",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of the container")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec,
        title=lambda: _("Kubernetes pod containers"),
    )
)
