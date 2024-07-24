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


def _form_printer_output() -> Dictionary:
    return Dictionary(
        elements={
            "capacity_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Capacity filled"),
                    form_spec_template=Percentage(),
                    migrate=migrate_to_float_simple_levels,
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint((80.0, 90.0)),
                ),
            )
        },
    )


rule_spec_printer_output = CheckParameters(
    name="printer_output",
    title=Title("Printer Output Units"),
    topic=Topic.PERIPHERALS,
    parameter_form=_form_printer_output,
    condition=HostAndItemCondition(item_title=Title("Unit name"), item_form=String()),
)
