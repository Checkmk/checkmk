#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    Float,
    InputHint,
    LevelDirection,
    migrate_to_float_simple_levels,
    SimpleLevels,
    String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        title=Title("Voltage levels"),
        elements={
            "levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Voltage Levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="V"),
                    migrate=migrate_to_float_simple_levels,
                    prefill_fixed_levels=InputHint((0.0, 0.0)),
                ),
            )
        },
    )


rule_spec_etherbox_voltage = CheckParameters(
    name="etherbox_voltage",
    title=Title("Etherbox voltage"),
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_make_form,
    condition=HostAndItemCondition(
        item_title=Title("Contact sensor type"),
        item_form=String(
            help_text=Help(
                "The item of etherbox checks is build as 'contact.sensor_type'."
                " For example, you want the rule to only apply to a temperature"
                " sensor (type 1) on contact 3 then set the item to 3.1 ."
            )
        ),
    ),
)
