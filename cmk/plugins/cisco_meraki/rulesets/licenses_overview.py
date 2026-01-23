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
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "remaining_expiration_time": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Time until license expiration"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=DefaultValue(
                        (
                            40 * 24 * 60 * 60,  # 40 days
                            20 * 24 * 60 * 60,  # 20 days
                        )
                    ),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.DAY],
                        custom_validate=(validators.NumberInRange(min_value=0),),
                    ),
                )
            ),
        },
    )


rule_spec_cisco_meraki_org_licenses_overview = CheckParameters(
    name="cisco_meraki_org_licenses_overview",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
    title=Title("Cisco Meraki licenses overview"),
    condition=HostAndItemCondition(item_title=Title("Organization")),
)
