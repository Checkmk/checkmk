#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.utils import mssql_item_spec_instance_tablespace
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import (
    Age,
    Alternative,
    Dictionary,
    DropdownChoice,
    FixedValue,
    MonitoringState,
    Transform,
    Tuple,
)


def _vs_mssql_backup_age(title: str) -> Alternative:
    return Alternative(
        title=title,
        elements=[
            Tuple(
                title=_("Set levels"),
                elements=[
                    Age(title=_("Warning if older than")),
                    Age(title=_("Critical if older than")),
                ],
            ),
            Tuple(
                title=_("No levels"),
                elements=[
                    FixedValue(value=None, totext=""),
                    FixedValue(value=None, totext=""),
                ],
            ),
        ],
    )


def _valuespec_discovery_mssql_backup():
    return Dictionary(
        title=_("MSSQL backup discovery"),
        elements=[
            (
                "mode",
                DropdownChoice(
                    title=_("Backup modes"),
                    choices=[
                        ("summary", _("Create a service for each instance")),
                        ("per_type", _("Create a service for each instance and backup type")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="discovery_mssql_backup",
        valuespec=_valuespec_discovery_mssql_backup,
    )
)


def _parameter_valuespec_mssql_backup():
    return Transform(
        valuespec=Dictionary(
            help=_(
                "This rule allows you to set limits on the age of backups for "
                "different backup types. If your agent does not support "
                "backup types (e.g. <i>Log Backup</i>, <i>Database Diff "
                "Backup</i>, etc.) you can use the option <i>Database Backup"
                "</i> to set a general limit"
            ),
            elements=[
                ("database", _vs_mssql_backup_age(_("Database backup"))),
                ("database_diff", _vs_mssql_backup_age(_("Database diff backup"))),
                ("log", _vs_mssql_backup_age(_("Log backup"))),
                ("file_or_filegroup", _vs_mssql_backup_age(_("File or filegroup backup"))),
                ("file_diff", _vs_mssql_backup_age(_("File diff backup"))),
                ("partial", _vs_mssql_backup_age(_("Partial backup"))),
                ("partial_diff", _vs_mssql_backup_age(_("Partial diff backup"))),
                ("unspecific", _vs_mssql_backup_age(_("Unspecific backup"))),
                ("not_found", MonitoringState(title=_("State if no backup found"))),
            ],
        ),
        forth=lambda params: (
            params
            if isinstance(params, dict)
            else {
                "database": (
                    params[0],
                    params[1],
                )
            }
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_backup",
        group=RulespecGroupCheckParametersApplications,
        item_spec=mssql_item_spec_instance_tablespace,
        parameter_valuespec=_parameter_valuespec_mssql_backup,
        title=lambda: _("MSSQL Backup summary"),
    )
)
