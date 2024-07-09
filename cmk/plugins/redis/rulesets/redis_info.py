#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    migrate_to_float_simple_levels,
    SimpleLevels,
    SingleChoice,
    SingleChoiceElement,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_redis_info():
    return Dictionary(
        elements={
            "expected_mode": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Expected mode"),
                    elements=[
                        SingleChoiceElement("standalone", Title("Standalone")),
                        SingleChoiceElement("sentinel", Title("Sentinel")),
                        SingleChoiceElement("cluster", Title("Cluster")),
                    ],
                ),
            ),
            "min": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.LOWER,
                    title=Title("Minimum allowed uptime"),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ]
                    ),
                    prefill_fixed_levels=DefaultValue(value=(0.0, 0.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
            "max": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    title=Title("Maximum allowed uptime"),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ]
                    ),
                    prefill_fixed_levels=DefaultValue(value=(0.0, 0.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
        }
    )


rule_spec_redis_info = CheckParameters(
    name="redis_info",
    title=Title("Redis info"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_redis_info,
    condition=HostAndItemCondition(item_title=Title("Redis server name")),
)
