#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, MonitoringState


def _parameter_valuespec_f5_bigip_cluster_v11():
    return Dictionary(
        title=_("Interpretation of Config Sync Status"),
        elements=[
            ("0", MonitoringState(title="Unknown", default_value=3)),
            ("1", MonitoringState(title="Syncing", default_value=0)),
            ("2", MonitoringState(title="Need Manual Sync", default_value=1)),
            ("3", MonitoringState(title="In Sync", default_value=0)),
            ("4", MonitoringState(title="Sync Failed", default_value=2)),
            ("5", MonitoringState(title="Sync Disconnected", default_value=2)),
            ("6", MonitoringState(title="Standalone", default_value=2)),
            ("7", MonitoringState(title="Awaiting Initial Sync", default_value=1)),
            ("8", MonitoringState(title="Incompatible Version", default_value=2)),
            ("9", MonitoringState(title="Partial Sync", default_value=2)),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="f5_bigip_cluster_v11",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_f5_bigip_cluster_v11,
        title=lambda: _("F5 BigIP configuration sync status"),
    )
)
