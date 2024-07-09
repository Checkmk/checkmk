#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
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
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_valuespec_jenkins_jobs() -> Dictionary:
    return Dictionary(
        elements={
            "jenkins_job_score": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Job score"),
                    form_spec_template=Integer(unit_symbol="%"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=InputHint(value=(0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                )
            ),
            "jenkins_last_build": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Time since last build"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                        ],
                    ),
                    prefill_fixed_levels=InputHint(value=(0.0, 0.0)),
                    migrate=migrate_to_float_simple_levels,
                )
            ),
            "jenkins_time_since": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Time since last successful build"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                        ],
                    ),
                    prefill_fixed_levels=InputHint(value=(0.0, 0.0)),
                    migrate=migrate_to_float_simple_levels,
                )
            ),
            "jenkins_build_duration": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Duration of last build"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                        ],
                    ),
                    prefill_fixed_levels=InputHint(value=(0.0, 0.0)),
                    migrate=migrate_to_float_simple_levels,
                )
            ),
            "job_state": DictElement(
                parameter_form=Dictionary(
                    title=Title("Override check state based on job state"),
                    elements={
                        "aborted": DictElement(
                            parameter_form=ServiceState(
                                title=Title("State when job is in state aborted"),
                                prefill=DefaultValue(0),
                            )
                        ),
                        "blue": DictElement(
                            parameter_form=ServiceState(
                                title=Title("State when job is in state success"),
                                prefill=DefaultValue(0),
                            )
                        ),
                        "disabled": DictElement(
                            parameter_form=ServiceState(
                                title=Title("State when job is in state disabled"),
                                prefill=DefaultValue(0),
                            )
                        ),
                        "notbuilt": DictElement(
                            parameter_form=ServiceState(
                                title=Title("State when job is in state not built"),
                                prefill=DefaultValue(0),
                            )
                        ),
                        "red": DictElement(
                            parameter_form=ServiceState(
                                title=Title("State when job is in state failed"),
                                prefill=DefaultValue(2),
                            )
                        ),
                        "yellow": DictElement(
                            parameter_form=ServiceState(
                                title=Title("State when job is in state unstable"),
                                prefill=DefaultValue(1),
                            )
                        ),
                    },
                ),
            ),
            "build_result": DictElement(
                parameter_form=Dictionary(
                    title=Title("Override check state based on last build result"),
                    elements={
                        "success": DictElement(
                            parameter_form=ServiceState(
                                title=Title("State when last build result is: success"),
                                prefill=DefaultValue(0),
                            )
                        ),
                        "unstable": DictElement(
                            parameter_form=ServiceState(
                                title=Title("State when last build result is: unstable"),
                                prefill=DefaultValue(0),
                            )
                        ),
                        "failure": DictElement(
                            parameter_form=ServiceState(
                                title=Title("State when last build result is: failed"),
                                prefill=DefaultValue(2),
                            )
                        ),
                        "aborted": DictElement(
                            parameter_form=ServiceState(
                                title=Title("State when last build result is: aborted"),
                                prefill=DefaultValue(0),
                            )
                        ),
                        "null": DictElement(
                            parameter_form=ServiceState(
                                title=Title(
                                    "State when last build result is: module not built (legacy)"
                                ),
                                help_text=Help("Only valid in Jenkins versions <= 1.622."),
                                prefill=DefaultValue(1),
                            )
                        ),
                        "not_built": DictElement(
                            parameter_form=ServiceState(
                                title=Title("State when last build result is: module not built"),
                                prefill=DefaultValue(1),
                            )
                        ),
                        "none": DictElement(
                            parameter_form=ServiceState(
                                title=Title("State when build result is: running"),
                                prefill=DefaultValue(0),
                            )
                        ),
                    },
                )
            ),
        },
    )


rule_spec_jenkins_jobs = CheckParameters(
    name="jenkins_jobs",
    topic=Topic.APPLICATIONS,
    condition=HostAndItemCondition(item_title=Title("Job name")),
    parameter_form=_parameter_valuespec_jenkins_jobs,
    title=Title("Jenkins jobs"),
)
