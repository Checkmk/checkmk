#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    Float,
    InputHint,
    LevelDirection,
    migrate_to_integer_simple_levels,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This ruleset allows you to configure levels for the deadlocks in the database"
        ),
        elements={
            "deadlocks": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Deadlocks"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(),
                    migrate=migrate_to_integer_simple_levels,
                    prefill_fixed_levels=InputHint((10, 100)),  # No default defined previously
                ),
            )
        },
    )


rule_spec_azure_databases_deadlock = CheckParameters(
    name="azure_databases_deadlock",
    title=Title("Azure SQL database deadlocks"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostAndItemCondition(item_title=Title("Database name")),
)
