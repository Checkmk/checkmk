#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    LevelsType,
    migrate_to_integer_simple_levels,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_jvm_requests() -> Dictionary:
    return Dictionary(
        elements={
            "levels_upper": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    title=Title("Upper levels for incoming requests to a JVM application server"),
                    form_spec_template=Integer(unit_symbol="requests/sec"),
                    prefill_fixed_levels=DefaultValue(value=(800, 1000)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "levels_lower": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.LOWER,
                    title=Title("Lower levels for incoming requests to a JVM application server"),
                    form_spec_template=Integer(unit_symbol="requests/sec"),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=DefaultValue(value=(10, 5)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        },
    )


rule_spec_jvm_requests = CheckParameters(
    name="jvm_requests",
    title=Title("JVM request count"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_jvm_requests,
    condition=HostAndItemCondition(item_title=Title("Name of the virtual machine")),
)
