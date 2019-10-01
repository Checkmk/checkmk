#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

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
                       style="dropdown",
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
        title=_("Discovery of MSSQL backup"),
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
