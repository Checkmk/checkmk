#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    Percentage,
    SimpleLevels,
    validators,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_valuespec_checkpoint_vsx_connections():
    return Dictionary(
        help_text=Help(
            "This rule allows you to configure the number of maximum connections for a given VSID."
        ),
        elements={
            "levels_perc": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Percentage of maximum available connections"),
                    form_spec_template=Percentage(),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=DefaultValue((80.0, 90.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
            "levels_abs": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Absolute number of connections"),
                    form_spec_template=Integer(
                        label=Label("connections"),
                        custom_validate=(validators.NumberInRange(0, None),),
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        },
    )


rule_spec_checkpoint_vsx_connections = CheckParameters(
    name="checkpoint_vsx_connections",
    title=Title("Check Point VSID connections"),
    topic=Topic.NETWORKING,
    parameter_form=_parameter_valuespec_checkpoint_vsx_connections,
    condition=HostAndItemCondition(item_title=Title("VSID")),
)
