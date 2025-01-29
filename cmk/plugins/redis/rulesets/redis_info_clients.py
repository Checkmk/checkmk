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


def _parameter_form_redis_info_clients():
    return Dictionary(
        elements={
            "connected_lower": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.LOWER,
                    title=Title("Lower levels on the total number of client connections"),
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "connected_upper": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    title=Title("Upper levels on the total number of client connections"),
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "output_lower": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.LOWER,
                    title=Title("Lower levels on the longest output list"),
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "output_upper": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    title=Title("Upper levels on the longest output list"),
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                )
            ),
            "input_lower": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    title=Title("Lower levels on the biggest input buffer"),
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "input_upper": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    title=Title("Upper levels on the biggest input buffer"),
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "blocked_lower": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.LOWER,
                    title=Title(
                        "Lower levels on the total number of clients pending on a blocking call"
                    ),
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "blocked_upper": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    title=Title(
                        "Upper levels on the total number of clients pending on a blocking call"
                    ),
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        }
    )


rule_spec_redis_info_clients = CheckParameters(
    name="redis_info_clients",
    title=Title("Redis clients"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_redis_info_clients,
    condition=HostAndItemCondition(item_title=Title("Redis clients")),
)
