#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.mssql.rulesets.utils import fs_mssql_backup_age
from cmk.rulesets.v1 import form_specs, Localizable, rule_specs, validators


def _parameter_form_mssql_backup_per_type():
    return form_specs.Dictionary(
        elements={
            "levels": fs_mssql_backup_age(Localizable("Upper levels for the backup age")),
        },
    )


def _item_spec() -> form_specs.Text:
    return form_specs.Text(
        title=Localizable("Instance, tablespace & backup type"),
        help_text=Localizable(
            "The MSSQL instance name, the tablespace name and the backup type, each separated "
            "by a space."
        ),
        custom_validate=validators.DisallowEmpty(),
    )


rule_spec_mssql_backup_per_type = rule_specs.CheckParameterWithItem(
    name="mssql_backup_per_type",
    topic=rule_specs.Topic.APPLICATIONS,
    item_form=_item_spec(),
    parameter_form=_parameter_form_mssql_backup_per_type,
    title=Localizable("MSSQL Backup"),
)
