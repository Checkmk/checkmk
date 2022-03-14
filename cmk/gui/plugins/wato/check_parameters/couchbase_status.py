#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, MonitoringState, TextInput


def _parameter_valuespec_couchbase_status():
    return Dictionary(
        title=_("Couchbase Node: Cluster status"),
        elements=[
            (
                "warmup_state",
                MonitoringState(
                    title=_('Resulting state if the status is "warmup"'),
                    default_value=0,
                ),
            ),
            (
                "unhealthy_state",
                MonitoringState(
                    title=_('Resulting state if the status is "unhealthy"'),
                    default_value=2,
                ),
            ),
            (
                "inactive_added_state",
                MonitoringState(
                    title=_('Resulting state if the cluster membership status is "inactiveAdded"'),
                    default_value=1,
                ),
            ),
            (
                "inactive_failed_state",
                MonitoringState(
                    title=_('Resulting state if the cluster membership status is "inactiveFailed"'),
                    default_value=2,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="couchbase_status",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        item_spec=lambda: TextInput(title=_("Node name")),
        parameter_valuespec=_parameter_valuespec_couchbase_status,
        title=lambda: _("Couchbase Status"),
    )
)
