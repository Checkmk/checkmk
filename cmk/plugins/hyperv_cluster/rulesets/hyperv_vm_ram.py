#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    Percentage,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

rule_spec_hyperv_vm_ram = CheckParameters(
    name="hyperv_vm_ram",
    title=Title("Hyper-V VM RAM"),
    topic=Topic.GENERAL,
    condition=HostCondition(),
    parameter_form=lambda: Dictionary(
        elements={
            "max_ram": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Max levels for ram"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=InputHint(value=(80, 90)),
                ),
            ),
            "min_ram": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Min levels for ram"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=InputHint(value=(20, 10)),
                ),
            ),
            "check_demand": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    label=Label("State if demand is higher than used RAM")
                ),
            ),
        }
    ),
)
