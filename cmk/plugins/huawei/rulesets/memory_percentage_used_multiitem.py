#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    LevelsType,
    migrate_to_float_simple_levels,
    Percentage,
    SimpleLevels,
    SimpleLevelsConfigModel,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_memory_percentage_used_multiitem() -> Dictionary:
    return Dictionary(
        elements={
            "levels": DictElement[SimpleLevelsConfigModel[float]](
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((80.0, 90.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
        },
    )


rule_spec_memory_percentage_used_multiitem = CheckParameters(
    name="memory_percentage_used_multiitem",
    title=Title("Memory percentage used of devices with modules"),
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=_parameter_form_memory_percentage_used_multiitem,
    condition=HostAndItemCondition(item_title=Title("Module")),
)
