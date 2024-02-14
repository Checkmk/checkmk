#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import cmk.rulesets.v1.form_specs.basic
from cmk.plugins.mssql.rulesets.utils import (
    fs_mssql_backup_age,
    mssql_condition_instance_tablespace,
)
from cmk.rulesets.v1 import form_specs, Localizable, rule_specs


def _form_spec_discovery_mssql_backup():
    return form_specs.composed.Dictionary(
        elements={
            "mode": form_specs.composed.DictElement(
                parameter_form=cmk.rulesets.v1.form_specs.basic.SingleChoice(
                    title=Localizable("Backup modes"),
                    elements=[
                        cmk.rulesets.v1.form_specs.basic.SingleChoiceElement(
                            name="summary",
                            title=Localizable("Create a service for each instance"),
                        ),
                        cmk.rulesets.v1.form_specs.basic.SingleChoiceElement(
                            name="per_type",
                            title=Localizable("Create a service for each instance and backup type"),
                        ),
                    ],
                ),
            )
        },
    )


rule_spec_discovery_mssql_backup = rule_specs.DiscoveryParameters(
    title=Localizable("MSSQL backup discovery"),
    topic=rule_specs.Topic.GENERAL,
    eval_type=rule_specs.EvalType.MERGE,
    name="discovery_mssql_backup",
    parameter_form=_form_spec_discovery_mssql_backup,
)


def _parameter_formspec_mssql_backup() -> form_specs.composed.Dictionary:
    return form_specs.composed.Dictionary(
        help_text=Localizable(
            "This rule allows you to set limits on the age of backups for "
            "different backup types. If your agent does not support "
            "backup types (e.g. <i>Log Backup</i>, <i>Database Diff "
            "Backup</i>, etc.) you can use the option <i>Database Backup"
            "</i> to set a general limit"
        ),
        elements={
            "database": fs_mssql_backup_age(Localizable("Database backup")),
            "database_diff": fs_mssql_backup_age(Localizable("Database diff backup")),
            "log": fs_mssql_backup_age(Localizable("Log backup")),
            "file_or_filegroup": fs_mssql_backup_age(Localizable("File or filegroup backup")),
            "file_diff": fs_mssql_backup_age(Localizable("File diff backup")),
            "partial": fs_mssql_backup_age(Localizable("Partial backup")),
            "partial_diff": fs_mssql_backup_age(Localizable("Partial diff backup")),
            "unspecific": fs_mssql_backup_age(Localizable("Unspecific backup")),
            "not_found": form_specs.composed.DictElement(
                parameter_form=form_specs.basic.ServiceState(
                    title=Localizable("State if no backup found")
                )
            ),
        },
    )


rule_spec_mssql_backup = rule_specs.CheckParameters(
    name="mssql_backup",
    title=Localizable("MSSQL Backup summary"),
    topic=rule_specs.Topic.APPLICATIONS,
    parameter_form=_parameter_formspec_mssql_backup,
    condition=mssql_condition_instance_tablespace(),
)
