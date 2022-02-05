#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, MonitoringState


def _parameter_valuespec_cluster_status():
    return Dictionary(
        elements=[
            (
                "type",
                DropdownChoice(
                    title=_("Cluster type"),
                    help=_("Expected cluster type."),
                    choices=[
                        ("active_standby", _("active / standby")),
                        ("active_active", _("active / active")),
                    ],
                    default_value="active_standby",
                ),
            ),
            (
                "v11_2_states",
                Dictionary(
                    title=_("Interpretation of failover cluster state"),
                    help=_(
                        "Here you can set the failover state for BIG-IP system of version 11.2.0"
                    ),
                    elements=[
                        ("0", MonitoringState(title="Unknown", default_value=3)),
                        ("1", MonitoringState(title="Offline", default_value=2)),
                        ("2", MonitoringState(title="Forced offline", default_value=2)),
                        ("3", MonitoringState(title="Standby", default_value=0)),
                        ("4", MonitoringState(title="Active", default_value=0)),
                    ],
                ),
            ),
        ],
        required_keys=["type"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="cluster_status",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cluster_status,
        title=lambda: _("Cluster status"),
    )
)
