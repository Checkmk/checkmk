#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.mssql.rulesets.utils import fs_mssql_backup_age
from cmk.rulesets.v1 import form_specs, Help, rule_specs, Title
from cmk.rulesets.v1.form_specs import validators


def _parameter_form_mssql_backup_per_type():
    return form_specs.Dictionary(
        elements={
            "levels": fs_mssql_backup_age(Title("Upper levels for the backup age")),
        },
    )


def _item_spec() -> form_specs.String:
    return form_specs.String(
        help_text=Help(
            "The MSSQL instance name, the tablespace name and the backup type, each separated "
            "by a space."
        ),
        custom_validate=(validators.LengthInRange(min_value=1),),
    )


rule_spec_mssql_backup_per_type = rule_specs.CheckParameters(
    name="mssql_backup_per_type",
    topic=rule_specs.Topic.APPLICATIONS,
    parameter_form=_parameter_form_mssql_backup_per_type,
    title=Title("MSSQL Backup"),
    condition=rule_specs.HostAndItemCondition(
        item_title=Title("Instance, tablespace & backup type"), item_form=_item_spec()
    ),
)
