#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
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
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_generic_numeric_value_without_item() -> Dictionary:
    return Dictionary(
        elements={
            "levels_upper": DictElement[SimpleLevelsConfigModel[float]](
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Upper threshold"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(),
                    prefill_fixed_levels=InputHint((0.0, 0.0)),
                ),
            ),
            "levels_lower": DictElement[SimpleLevelsConfigModel[float]](
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Lower threshold"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Float(),
                    prefill_fixed_levels=InputHint((0.0, 0.0)),
                ),
            ),
        }
    )


rule_spec_generic_numeric_value_without_item = CheckParameters(
    name="generic_numeric_value_without_item",
    topic=Topic.GENERAL,
    parameter_form=_parameter_form_generic_numeric_value_without_item,
    title=Title("Generic numeric value (without item)"),
    condition=HostCondition(),
)
