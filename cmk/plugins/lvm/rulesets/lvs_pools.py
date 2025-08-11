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
    Percentage,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_lvm_lvs_pools() -> Dictionary:
    return Dictionary(
        elements={
            "levels_meta": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Levels for meta"),
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue((80.0, 90.0)),
                    level_direction=LevelDirection.UPPER,
                    migrate=migrate_to_float_simple_levels,
                )
            ),
            "levels_data": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Levels for Data"),
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue((80.0, 90.0)),
                    level_direction=LevelDirection.UPPER,
                    migrate=migrate_to_float_simple_levels,
                )
            ),
        }
    )


rule_spec_lvm_lvs_pools = CheckParameters(
    name="lvm_lvs_pools",
    title=Title("Logical Volume Pools (LVM)"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_form_lvm_lvs_pools,
    condition=HostAndItemCondition(item_title=Title("Logical Volume Pool")),
)
