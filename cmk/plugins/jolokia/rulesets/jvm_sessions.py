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
    migrate_to_integer_simple_levels,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_jvm_sessions() -> Dictionary:
    return Dictionary(
        elements={
            "levels_upper": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    title=Title("Upper levels"),
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue(value=(800, 1000)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "levels_lower": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.LOWER,
                    title=Title("Lower levels"),
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue(value=(-1, -1)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        }
    )


rule_spec_jvm_sessions = CheckParameters(
    name="jvm_sessions",
    title=Title("JVM session count"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_jvm_sessions,
    condition=HostAndItemCondition(item_title=Title("Name of the virtual machine")),
)
