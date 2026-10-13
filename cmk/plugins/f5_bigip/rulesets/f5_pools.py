#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
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


def _parameter_formspec_f5_pools() -> Dictionary:
    return Dictionary(
        title=Title("F5 load balancer pools"),
        elements={
            "levels_lower": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Minimum number of pool members"),
                    level_direction=LevelDirection.LOWER,
                    migrate=migrate_to_integer_simple_levels,
                    form_spec_template=Integer(unit_symbol="Members"),
                    prefill_fixed_levels=DefaultValue((2, 1)),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                )
            )
        },
    )


rule_spec_f5_pools = CheckParameters(
    name="f5_pools",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_formspec_f5_pools,
    title=Title("F5 load balancer pools"),
    condition=HostAndItemCondition(item_title=Title("Instance name")),
)
