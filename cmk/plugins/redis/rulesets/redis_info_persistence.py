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
    ServiceState,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_redis_info_persistence():
    return Dictionary(
        elements={
            "rdb_last_bgsave_state": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when last RDB save operation was faulty"),
                    prefill=DefaultValue(value=ServiceState.WARN),
                ),
            ),
            "aof_last_rewrite_state": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when Last AOF rewrite operation was faulty"),
                    prefill=DefaultValue(value=ServiceState.WARN),
                ),
            ),
            "rdb_changes_count": DictElement(
                parameter_form=SimpleLevels(
                    level_direction=LevelDirection.UPPER,
                    title=Title("Number of changes since last dump"),
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        }
    )


rule_spec_redis_info_persistence = CheckParameters(
    name="redis_info_persistence",
    title=Title("Redis persistence"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_redis_info_persistence,
    condition=HostAndItemCondition(item_title=Title("Redis server name")),
)
