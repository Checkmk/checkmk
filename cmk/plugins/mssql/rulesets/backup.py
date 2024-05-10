#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.mssql.rulesets.utils import (
    fs_mssql_backup_age,
    mssql_condition_instance_tablespace,
)
from cmk.rulesets.v1 import form_specs, Help, rule_specs, Title


def _form_spec_discovery_mssql_backup():
    return form_specs.Dictionary(
        elements={
            "mode": form_specs.DictElement(
                parameter_form=form_specs.SingleChoice(
                    title=Title("Backup modes"),
                    elements=[
                        form_specs.SingleChoiceElement(
                            name="summary",
                            title=Title("Create a service for each instance"),
                        ),
                        form_specs.SingleChoiceElement(
                            name="per_type",
                            title=Title("Create a service for each instance and backup type"),
                        ),
                    ],
                ),
            )
        },
    )


rule_spec_discovery_mssql_backup = rule_specs.DiscoveryParameters(
    title=Title("MSSQL backup discovery"),
    topic=rule_specs.Topic.GENERAL,
    name="discovery_mssql_backup",
    parameter_form=_form_spec_discovery_mssql_backup,
)


def _parameter_formspec_mssql_backup() -> form_specs.Dictionary:
    return form_specs.Dictionary(
        help_text=Help(
            "This rule allows you to set limits on the age of backups for "
            "different backup types. If your agent does not support "
            "backup types (e.g. <i>Log Backup</i>, <i>Database Diff "
            "Backup</i>, etc.) you can use the option <i>Database Backup"
            "</i> to set a general limit"
        ),
        elements={
            "database": fs_mssql_backup_age(Title("Database backup")),
            "database_diff": fs_mssql_backup_age(Title("Database diff backup")),
            "log": fs_mssql_backup_age(Title("Log backup")),
            "file_or_filegroup": fs_mssql_backup_age(Title("File or filegroup backup")),
            "file_diff": fs_mssql_backup_age(Title("File diff backup")),
            "partial": fs_mssql_backup_age(Title("Partial backup")),
            "partial_diff": fs_mssql_backup_age(Title("Partial diff backup")),
            "unspecific": fs_mssql_backup_age(Title("Unspecific backup")),
            "not_found": form_specs.DictElement(
                parameter_form=form_specs.ServiceState(title=Title("State if no backup found"))
            ),
        },
    )


rule_spec_mssql_backup = rule_specs.CheckParameters(
    name="mssql_backup",
    title=Title("MSSQL Backup summary"),
    topic=rule_specs.Topic.APPLICATIONS,
    parameter_form=_parameter_formspec_mssql_backup,
    condition=mssql_condition_instance_tablespace(),
)
