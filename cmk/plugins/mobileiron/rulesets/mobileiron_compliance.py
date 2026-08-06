#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    LevelsType,
    migrate_to_integer_simple_levels,
    SimpleLevels,
    SimpleLevelsConfigModel,
    validators,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_mobileiron_compliance() -> Dictionary:
    return Dictionary(
        elements={
            "policy_violation_levels": DictElement[SimpleLevelsConfigModel[int]](
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Upper levels for the policy violation count"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(
                        label=Label("violations"),
                        custom_validate=(validators.NumberInRange(0, None),),
                    ),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((2, 3)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "ignore_compliance": DictElement[bool](
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Configure compliance state checking"),
                    label=Label("Ignore compliance state"),
                    prefill=DefaultValue(False),
                ),
            ),
        },
    )


rule_spec_mobileiron_compliance = CheckParameters(
    name="mobileiron_compliance",
    # weblate-flags: read-only, vendor-name
    title=Title("MobileIron compliance"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_mobileiron_compliance,
    condition=HostCondition(),
)
