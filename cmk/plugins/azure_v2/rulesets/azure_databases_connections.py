# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This ruleset allows you to configure levels for Azure SQL database connections"
        ),
        elements={
            "successful_connections_lower": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels for successful connections"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((1, 0)),
                ),
            ),
            "successful_connections": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for successful connections"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((10, 15)),
                ),
            ),
            "failed_connections": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Failed connections"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((1, 5)),
                ),
            ),
        },
    )


rule_spec_azure_databases_connections = CheckParameters(
    name="azure_v2_databases_connections",
    title=Title("Azure SQL database connections"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostAndItemCondition(item_title=Title("Database")),
)
