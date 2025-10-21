#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    LevelDirection,
    LevelsType,
    migrate_to_float_simple_levels,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_valuespec_hyperv_vm_checkpoints() -> Dictionary:
    return Dictionary(
        elements={
            "age": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Age of the latest checkpoint"),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ],
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_levels_type=DefaultValue(LevelsType.NONE),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
            "age_oldest": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Age of the oldest checkpoint"),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ],
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint((10 * 86400, 20 * 86400)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
        },
        help_text=Help(
            "Configure age thresholds for VM checkpoints. "
            "You can set warning and critical levels for both the newest and oldest checkpoints."
        ),
    )


rule_spec_hyperv_vm_checkpoints = CheckParameters(
    name="hyperv_vm_checkpoints",
    title=Title("Hyper-V VM Checkpoints"),
    topic=Topic.APPLICATIONS,
    condition=HostCondition(),
    parameter_form=_parameter_valuespec_hyperv_vm_checkpoints,
)
