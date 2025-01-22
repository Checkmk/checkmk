#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    ServiceState,
    SIMagnitude,
    SimpleLevels,
    SingleChoice,
    SingleChoiceElement,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_valuespec_jenkins_nodes() -> Dictionary:
    return Dictionary(
        elements={
            "jenkins_offline": DictElement(
                parameter_form=ServiceState(
                    title=Title("Node state: Offline"),
                    prefill=DefaultValue(ServiceState.CRIT),
                )
            ),
            "jenkins_mode": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Expected mode state."),
                    help_text=Help(
                        "Choose between Normal (Utilize this node as much "
                        "as possible) and Exclusive (Only build jobs with label "
                        "restrictions matching this node). The state will "
                        "change to warning state, if the mode differs."
                    ),
                    elements=[
                        SingleChoiceElement(name="NORMAL", title=Title("Normal")),
                        SingleChoiceElement(name="EXCLUSIVE", title=Title("Exclusive")),
                    ],
                    prefill=DefaultValue("NORMAL"),
                )
            ),
            "jenkins_numexecutors": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Lower level for number of executors of this node"),
                    form_spec_template=Integer(),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                )
            ),
            "jenkins_numexecutors_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Upper level for number of executors of this node"),
                    form_spec_template=Integer(),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                )
            ),
            "jenkins_busyexecutors_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Lower level for number of busy executors of this node"),
                    form_spec_template=Integer(),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                )
            ),
            "jenkins_busyexecutors": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Upper level for number of busy executors of this node"),
                    form_spec_template=Integer(),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                )
            ),
            "jenkins_idleexecutors_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Lower level for number of idle executors of this node"),
                    form_spec_template=Integer(),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                )
            ),
            "jenkins_idleexecutors": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Upper level for number of idle executors of this node"),
                    form_spec_template=Integer(),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                )
            ),
            "avg_response_time": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Average round-trip response time to this node"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                            TimeMagnitude.MILLISECOND,
                        ],
                    ),
                    prefill_fixed_levels=InputHint(value=(0.0, 0.0)),
                    migrate=migrate_to_float_simple_levels,
                )
            ),
            "jenkins_clock": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Clock difference"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                            TimeMagnitude.MILLISECOND,
                        ],
                    ),
                    prefill_fixed_levels=InputHint(value=(0.0, 0.0)),
                    migrate=migrate_to_float_simple_levels,
                )
            ),
            "jenkins_temp": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Absolute levels for free temp space"),
                    form_spec_template=DataSize(
                        displayed_magnitudes=[
                            SIMagnitude.GIGA,
                            SIMagnitude.MEGA,
                        ]
                    ),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                    migrate=lambda old_levels: migrate_to_integer_simple_levels(
                        old_levels,
                        # The value from the plug-in before its rewrite was entered to be in
                        # megabytes and the conversion to bytes had been performed inside the
                        # check itself.
                        # We convert the value to comply with megabytes values of the new API.
                        scale=1000,
                    ),
                )
            ),
        },
    )


rule_spec_jenkins_nodes = CheckParameters(
    name="jenkins_nodes",
    topic=Topic.APPLICATIONS,
    condition=HostAndItemCondition(item_title=Title("Node name")),
    parameter_form=_parameter_valuespec_jenkins_nodes,
    title=Title("Jenkins nodes"),
)
