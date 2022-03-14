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


def _parameter_valuespec_mssql_databases():
    return Dictionary(
        elements=[
            (
                "map_db_states",
                Dictionary(
                    elements=[
                        ("ONLINE", MonitoringState(title=_("Database Online"))),
                        ("OFFLINE", MonitoringState(title=_("Database Offline"))),
                        ("RESTORING", MonitoringState(title=_("Database Files are restored"))),
                        ("RECOVERING", MonitoringState(title=_("Database is being recovered"))),
                        (
                            "RECOVERY_PENDING",
                            MonitoringState(title=_("Database must be recovered")),
                        ),
                        ("SUSPECT", MonitoringState(title=_("Database Suspect"))),
                        ("EMERGENCY", MonitoringState(title=_("Database changed to emergency"))),
                    ],
                    title=_("Map Database States"),
                    optional_keys=[],
                ),
            ),
            (
                "map_auto_close_state",
                Dictionary(
                    elements=[
                        ("on", MonitoringState(title=_("Auto close on"), default_value=1)),
                        ("off", MonitoringState(title=_("Auto close off"))),
                    ],
                    title=_("Map auto close status"),
                    optional_keys=[],
                ),
            ),
            (
                "map_auto_shrink_state",
                Dictionary(
                    elements=[
                        ("on", MonitoringState(title=_("Auto shrink on"), default_value=1)),
                        ("off", MonitoringState(title=_("Auto shrink off"))),
                    ],
                    title=_("Map auto shrink status"),
                    optional_keys=[],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_databases",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Database identifier"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mssql_databases,
        title=lambda: _("MSSQL Databases properties"),
    )
)
