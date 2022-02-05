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


def _item_spec_mssql_mirroring():
    return TextInput(
        title=_("Database Name"),
        help=_(
            "You can set explicit databases to which you want to apply "
            "criticalities of the mirroring state."
        ),
        allow_empty=False,
    )


def _parameter_valuespec_mssql_mirroring():
    return Dictionary(
        help=_(
            "Set the criticalities of the mirroring state of database instances that "
            "have mirroring configured on Microsoft SQL server. Databases that do not have "
            "mirroring configured are not discovered. Note: mirroring information is only "
            "shown as a service on the server that hosts the principal database. It is NOT "
            "shown on any servers that host the mirror databases. This is to avoid duplicate "
            "service states and alerts. We therefore recommend to cluster these services."
        ),
        elements=[
            (
                "mirroring_state_criticality",
                MonitoringState(
                    default_value=0,
                    title=_("Mirroring state criticality"),
                    help=_(
                        "The criticality of the service when the mirroring state is not "
                        "'SYNCHRONIZED'. The default state is OK."
                    ),
                ),
            ),
            (
                "mirroring_witness_state_criticality",
                MonitoringState(
                    default_value=0,
                    title=_("Mirroring witness state criticality"),
                    help=_(
                        "The criticality of the service when the mirroring witness state "
                        "is not 'CONNECTED'. The default state is OK."
                    ),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_mirroring",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_mssql_mirroring,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mssql_mirroring,
        title=lambda: _("MSSQL Mirroring State"),
    )
)
