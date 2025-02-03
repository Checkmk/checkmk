#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    migrate_to_float_simple_levels,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This ruleset allows you to configure levels for the used storage space in percent"
        ),
        elements={
            "storage_percent": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Used storage"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="%"),
                    migrate=migrate_to_float_simple_levels,
                    prefill_fixed_levels=DefaultValue((85.0, 95.0)),
                ),
            )
        },
    )


rule_spec_azure_databases_storage = CheckParameters(
    name="azure_databases_storage",
    title=Title("Azure SQL database storage"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostAndItemCondition(item_title=Title("Database name")),
)
