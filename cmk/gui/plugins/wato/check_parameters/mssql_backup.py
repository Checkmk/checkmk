#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Age,
    Alternative,
    Dictionary,
    DropdownChoice,
    FixedValue,
    MonitoringState,
    TextAscii,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
    HostRulespec,
)


def _vs_mssql_backup_age(title):
    return Alternative(title=_("%s" % title),
                       elements=[
                           Tuple(title=_("Set levels"),
                                 elements=[
                                     Age(title=_("Warning if older than")),
                                     Age(title=_("Critical if older than")),
                                 ]),
                           Tuple(title=_("No levels"),
                                 elements=[
                                     FixedValue(None, totext=""),
                                     FixedValue(None, totext=""),
                                 ]),
                       ])


def _valuespec_discovery_mssql_backup():
    return Dictionary(
        title=_("MSSQL backup discovery"),
        elements=[
            ("mode",
             DropdownChoice(title=_("Backup modes"),
                            choices=[
                                ("summary", _("Create a service for each instance")),
                                ("per_type",
                                 _("Create a service for each instance and backup type")),
                            ])),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="discovery_mssql_backup",
        valuespec=_valuespec_discovery_mssql_backup,
    ))


def _parameter_valuespec_mssql_backup():
    return Transform(Dictionary(
        help=_("This rule allows you to set limits on the age of backups for "
               "different backup types. If your agent does not support "
               "backup types (e.g. <i>Log Backup</i>, <i>Database Diff "
               "Backup</i>, etc.) you can use the option <i>Database Backup"
               "</i> to set a general limit"),
        elements=[
            ("database", _vs_mssql_backup_age("Database backup")),
            ("database_diff", _vs_mssql_backup_age("Database diff backup")),
            ("log", _vs_mssql_backup_age("Log backup")),
            ("file_or_filegroup", _vs_mssql_backup_age("File or filegroup backup")),
            ("file_diff", _vs_mssql_backup_age("File diff backup")),
            ("partial", _vs_mssql_backup_age("Partial backup")),
            ("partial_diff", _vs_mssql_backup_age("Partial diff backup")),
            ("unspecific", _vs_mssql_backup_age("Unspecific backup")),
            ("not_found", MonitoringState(title=_("State if no backup found"))),
        ]),
                     forth=lambda params: (params if isinstance(params, dict) else {
                         'database': (
                             params[0],
                             params[1],
                         )
                     }))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_backup",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Service descriptions"), allow_empty=False),
        parameter_valuespec=_parameter_valuespec_mssql_backup,
        title=lambda: _("MSSQL Backup summary"),
    ))
