#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    migrate_to_float_simple_levels,
    Percentage,
    SimpleLevels,
    String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _form_printer_input() -> Dictionary:
    return Dictionary(
        elements={
            "capacity_levels": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Capacity remaining"),
                    form_spec_template=Percentage(),
                    migrate=migrate_to_float_simple_levels,
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=InputHint((20.0, 10.0)),
                ),
            )
        },
    )


rule_spec_printer_input = CheckParameters(
    name="printer_input",
    title=Title("Printer Input Units"),
    topic=Topic.PERIPHERALS,
    parameter_form=_form_printer_input,
    condition=HostAndItemCondition(
        item_title=Title("Unit name"),
        item_form=String(),
    ),
)
