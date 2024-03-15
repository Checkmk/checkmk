#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import form_specs, Help, rule_specs, Title


def fs_mssql_backup_age(
    title: Title,
) -> form_specs.DictElement[form_specs.SimpleLevelsConfigModel[float]]:
    return form_specs.DictElement(
        parameter_form=form_specs.SimpleLevels[float](
            title=title,
            level_direction=form_specs.LevelDirection.UPPER,
            form_spec_template=form_specs.TimeSpan(
                displayed_magnitudes=tuple(form_specs.TimeMagnitude)
            ),
            migrate=form_specs.migrate_to_float_simple_levels,
            prefill_fixed_levels=form_specs.InputHint(value=(0.0, 0.0)),
        )
    )


def mssql_condition_instance_tablespace() -> rule_specs.HostAndItemCondition:
    return rule_specs.HostAndItemCondition(
        item_title=Title("Instance & tablespace name"),
        item_form=form_specs.String(
            help_text=Help("The MSSQL instance name and the tablespace name separated by a space."),
            custom_validate=(form_specs.validators.LengthInRange(min_value=1),),
        ),
    )
