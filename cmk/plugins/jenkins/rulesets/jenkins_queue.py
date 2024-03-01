#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    ServiceState,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_valuespec_jenkins_queue() -> Dictionary:
    return Dictionary(
        elements={
            "queue_length": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Upper level for queue length"),
                    form_spec_template=Integer(unit_symbol="Tasks"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                )
            ),
            "in_queue_since": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Task in queue since"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ],
                    ),
                    prefill_fixed_levels=InputHint(value=(3600, 7200)),
                    migrate=migrate_to_float_simple_levels,
                )
            ),
            "stuck": DictElement(
                parameter_form=ServiceState(
                    title=Title("Task state: Stuck"),
                    prefill=DefaultValue(ServiceState.CRIT),
                )
            ),
            "jenkins_stuck_tasks": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Upper level for stuck tasks"),
                    form_spec_template=Integer(unit_symbol="Tasks"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint(value=(1, 2)),
                    migrate=migrate_to_integer_simple_levels,
                )
            ),
            "blocked": DictElement(
                parameter_form=ServiceState(
                    title=Title("Task state: Blocked"),
                    prefill=DefaultValue(ServiceState.OK),
                )
            ),
            "jenkins_blocked_tasks": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Upper level for blocked tasks"),
                    form_spec_template=Integer(unit_symbol="Tasks"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                )
            ),
            "pending": DictElement(
                parameter_form=ServiceState(
                    title=Title("Task state: Pending"),
                    prefill=DefaultValue(ServiceState.OK),
                )
            ),
            "jenkins_pending_tasks": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Upper level for pending tasks"),
                    form_spec_template=Integer(unit_symbol="Tasks"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                )
            ),
        },
    )


rule_spec_jenkins_queue = CheckParameters(
    name="jenkins_queue",
    topic=Topic.APPLICATIONS,
    condition=HostCondition(),
    parameter_form=_parameter_valuespec_jenkins_queue,
    title=Title("Jenkins queue"),
)
