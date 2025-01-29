#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DictElement,
    Dictionary,
    IECMagnitude,
    InputHint,
    Integer,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_valuespec_jenkins_system_metrics() -> Dictionary:
    return Dictionary(
        elements={
            "jenkins_threads_vm_deadlock_count": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Upper level for deadlocked threads"),
                    form_spec_template=Integer(unit_symbol="threads"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                )
            ),
            "jenkins_memory_vm_memory_total_used": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Upper level for memory used by JVM"),
                    form_spec_template=DataSize(
                        displayed_magnitudes=[
                            IECMagnitude.GIBI,
                            IECMagnitude.MEBI,
                        ]
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                )
            ),
        },
    )


rule_spec_jenkins_system_metrics = CheckParameters(
    name="jenkins_system_metrics",
    topic=Topic.APPLICATIONS,
    condition=HostAndItemCondition(item_title=Title("Metrics Group")),
    parameter_form=_parameter_valuespec_jenkins_system_metrics,
    title=Title("Jenkins system metrics"),
)
