#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    Float,
    InputHint,
    LevelDirection,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This ruleset allows you to configure levels for Azure Redis CPU utilization monitoring"
        ),
        elements={
            "for_time": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Levels over an extended period of time"),
                    elements={
                        "threshold_for_time": DictElement(
                            required=True,
                            parameter_form=Float(
                                title=Title("CPU utilization %"),
                                prefill=InputHint(0.0),
                                unit_symbol="%",
                            ),
                        ),
                        "limit_secs_for_time": DictElement(
                            required=True,
                            parameter_form=SimpleLevels(
                                title=Title("Alert after being at or above the threshold for"),
                                level_direction=LevelDirection.UPPER,
                                form_spec_template=TimeSpan(
                                    displayed_magnitudes=[
                                        TimeMagnitude.DAY,
                                        TimeMagnitude.HOUR,
                                        TimeMagnitude.MINUTE,
                                        TimeMagnitude.SECOND,
                                    ]
                                ),
                                prefill_fixed_levels=InputHint((0, 0)),
                            ),
                        ),
                    },
                ),
            ),
            "average_mins": DictElement(
                required=False,
                parameter_form=TimeSpan(
                    displayed_magnitudes=[TimeMagnitude.MINUTE],
                    help_text=Help(
                        "Average the instantaneous load over the specified number of minutes. "
                        'Note: This does NOT affect "Levels an extended period of time" above, '
                        "which always checks the instantaneous value."
                    ),
                    title=Title("Average over"),
                ),
            ),
            "cpu_utilization": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("CPU utilization"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Float(),
                    prefill_fixed_levels=InputHint((70.0, 80.0)),
                ),
            ),
        },
    )


rule_spec_azure_redis_cpu_utilization = CheckParameters(
    name="azure_redis_cpu_utilization",
    title=Title("Azure Redis CPU utilization"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form,
    condition=HostCondition(),
)
