#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    migrate_to_float_simple_levels,
    SimpleLevels,
    SimpleLevelsConfigModel,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_ups_test() -> Dictionary:
    return Dictionary(
        elements={
            "levels_elapsed_time": DictElement[SimpleLevelsConfigModel[float]](
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Time since last UPS selftest"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ]
                    ),
                    migrate=migrate_to_float_simple_levels,
                    prefill_fixed_levels=InputHint((0.0, 0.0)),
                ),
            )
        }
    )


rule_spec_ups_test = CheckParameters(
    name="ups_test",
    title=Title("UPS selftest"),
    topic=Topic.ENVIRONMENTAL,
    parameter_form=_parameter_form_ups_test,
    condition=HostCondition(),
)
