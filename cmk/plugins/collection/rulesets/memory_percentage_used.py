#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    LevelsType,
    migrate_to_float_simple_levels,
    Percentage,
    SimpleLevels,
    SimpleLevelsConfigModel,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_memory_utilization() -> Dictionary:
    return Dictionary(
        elements={
            "levels": DictElement[SimpleLevelsConfigModel[float]](
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Upper thresholds"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=InputHint((70.0, 80.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
        }
    )


rule_spec_memory_utilization_percentage = CheckParameters(
    name="memory_percentage_used",
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=_parameter_form_memory_utilization,
    title=Title("Memory utilization"),
    condition=HostCondition(),
)
