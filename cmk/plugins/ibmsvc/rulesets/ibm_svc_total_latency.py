#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_ibm_svc_total_latency() -> Dictionary:
    return Dictionary(
        elements={
            "read": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Read latency"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="ms"),
                    prefill_fixed_levels=InputHint((50.0, 100.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
            "write": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Write latency"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(unit_symbol="ms"),
                    prefill_fixed_levels=InputHint((50.0, 100.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
        },
    )


rule_spec_ibm_svc_total_latency = CheckParameters(
    name="ibm_svc_total_latency",
    title=Title("IBM SVC total disk latency"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_form_ibm_svc_total_latency,
    condition=HostAndItemCondition(
        item_title=Title("Disk/Drive type"),
        item_form=SingleChoice(
            help_text=Help("The type of disk/drive the latency levels apply to."),
            elements=[
                SingleChoiceElement(name="Drives", title=Title("Total latency for all drives")),
                SingleChoiceElement(name="MDisks", title=Title("Total latency for all MDisks")),
                SingleChoiceElement(name="VDisks", title=Title("Total latency for all VDisks")),
            ],
        ),
    ),
)
