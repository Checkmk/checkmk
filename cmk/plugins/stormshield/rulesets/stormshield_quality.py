#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    LevelDirection,
    Percentage,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_quality() -> Dictionary:
    return Dictionary(
        elements={
            "quality": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Lower levels on quality"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue(value=(80.0, 50.0)),
                ),
            )
        },
    )


rule_spec_stormshield_quality = CheckParameters(
    name="stormshield_quality",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_quality,
    title=Title("Stormshield quality"),
    condition=HostAndItemCondition(item_title=Title("Node index")),
)
