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
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_rulespec_scratch_tapes() -> Dictionary:
    return Dictionary(
        elements={
            "levels_lower": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Number of tapes in the scratch pool"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((7, 5)),
                ),
            ),
        },
    )


rule_spec_acme_sbc_snmp = CheckParameters(
    parameter_form=_parameter_rulespec_scratch_tapes,
    name="scratch_tapes",
    title=Title("IBM TSM: number of tapes in scratch pool"),
    topic=Topic.STORAGE,
    condition=HostAndItemCondition(item_title=Title("Scratch Pool")),
)
