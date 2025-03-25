#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    Percentage,
    SimpleLevels,
    SimpleLevelsConfigModel,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _generic_percentage_value_form() -> Dictionary:
    return Dictionary(
        elements={
            "upper_levels": DictElement[SimpleLevelsConfigModel[float]](
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=InputHint((80, 90)),
                ),
            )
        }
    )


rule_spec_generic_percentage_value = CheckParameters(
    name="generic_percentage_value",
    title=Title("Generic percentage value"),
    topic=Topic.GENERAL,
    parameter_form=_generic_percentage_value_form,
    condition=HostCondition(),
)
