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


def _parameter_valuespec_sap_hana_replication_status():
    return Dictionary(
        elements=[
            (
                "state_unknown",
                MonitoringState(
                    title=_("State in case of unknown status from replication script"),
                    default_value=3,
                ),
            ),
            (
                "state_no_replication",
                MonitoringState(title=_("State in case of no system replication"), default_value=2),
            ),
            (
                "state_error",
                MonitoringState(title=_("State when replication state is error"), default_value=2),
            ),
            (
                "state_replication_unknown",
                MonitoringState(
                    title=_("State when replication state is unknown"), default_value=2
                ),
            ),
            (
                "state_initializing",
                MonitoringState(
                    title=_("State when replication state is intializing"), default_value=1
                ),
            ),
            (
                "state_syncing",
                MonitoringState(
                    title=_("State when replication state is syncing"), default_value=0
                ),
            ),
            (
                "state_active",
                MonitoringState(title=_("State when replication state is active"), default_value=0),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="sap_hana_replication_status",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("The instance name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_sap_hana_replication_status,
        title=lambda: _("SAP HANA replication status"),
    )
)
