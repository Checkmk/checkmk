#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    LevelsType,
    migrate_to_integer_simple_levels,
    SimpleLevels,
    SimpleLevelsConfigModel,
    validators,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_pulse_secure_users() -> Dictionary:
    return Dictionary(
        elements={
            "upper_number_of_users": DictElement[SimpleLevelsConfigModel[int]](
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for the number of signed-in web users"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(
                        label=Label("users"),
                        custom_validate=(validators.NumberInRange(0, None),),
                    ),
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=InputHint((100, 200)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        },
    )


rule_spec_pulse_secure_users = CheckParameters(
    name="pulse_secure_users",
    # weblate-flags: read-only, vendor-name
    title=Title("Pulse Secure users"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_pulse_secure_users,
    condition=HostCondition(),
)
