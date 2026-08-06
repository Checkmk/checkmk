#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
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


def _parameter_form_checkpoint_connections() -> Dictionary:
    return Dictionary(
        elements={
            "levels": DictElement[SimpleLevelsConfigModel[int]](
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Maximum number of firewall connections"),
                    help_text=Help(
                        "This rule sets limits to the current number of connections "
                        "through a Check Point firewall."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(
                        label=Label("connections"),
                        custom_validate=(validators.NumberInRange(0, None),),
                    ),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((40000, 50000)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        },
    )


rule_spec_checkpoint_connections = CheckParameters(
    name="checkpoint_connections",
    # weblate-flags: read-only, vendor-name
    title=Title("Check Point firewall connections"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_checkpoint_connections,
    condition=HostCondition(),
)
