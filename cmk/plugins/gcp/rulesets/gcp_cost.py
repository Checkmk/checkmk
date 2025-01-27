#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    Float,
    InputHint,
    LevelDirection,
    SimpleLevels,
    SimpleLevelsConfigModel,
)
from cmk.rulesets.v1.form_specs._migrations import (
    migrate_to_float_simple_levels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def migrate_to_float_simple_levels_ignoring_predictive(
    value: object,
) -> SimpleLevelsConfigModel[float]:
    match value:
        case ("cmk_postprocessed", "predictive_levels", val_dict) | val_dict if isinstance(
            val_dict, dict
        ):
            return ("no_levels", None)
        case _:
            return migrate_to_float_simple_levels(value)


def _parameter_valuespec_gcp_cost() -> Dictionary:
    return Dictionary(
        title=Title("Levels monthly GCP costs"),
        elements={
            "levels": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    title=Title("Amount in billed currency"),
                    form_spec_template=Float(),
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                    migrate=migrate_to_float_simple_levels_ignoring_predictive,
                )
            ),
        },
    )


rule_spec_gcp_cost = CheckParameters(
    name="gcp_cost",
    title=Title("GCP Cost"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_valuespec_gcp_cost,
    condition=HostAndItemCondition(item_title=Title("Project")),
)
