#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    Integer,
    LevelDirection,
    LevelsType,
    migrate_to_float_simple_levels,
    Percentage,
    ServiceState,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_valuespec_apc_symentra() -> Dictionary:
    return Dictionary(
        elements={
            "capacity": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Levels of battery capacity"),
                    migrate=migrate_to_float_simple_levels,
                    level_direction=LevelDirection.LOWER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((95.0, 80.0)),
                    form_spec_template=Float(),
                ),
            ),
            "calibration_state": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State if calibration is invalid"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "post_calibration_levels": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Levels of battery parameters after diagnostics"),
                    help_text=Help(
                        "After a battery diagnostics the battery capacity is reduced until the "
                        "battery is fully charged again. Here you can specify an alternative "
                        "lower level in this post-diagnostics phase. "
                        "Since apc devices remember the time of the last diagnostics only "
                        "as a date, the alternative lower level will be applied on the whole "
                        "day of the diagnostics until midnight. You can extend this time period "
                        "with an additional time span to make sure diagnostics occuring just "
                        "before midnight do not trigger false alarms."
                    ),
                    elements={
                        "altcapacity": DictElement(
                            required=True,
                            parameter_form=Percentage(
                                title=Title(
                                    "Alternative critical battery capacity after diagnostics"
                                ),
                                prefill=DefaultValue(50),
                            ),
                        ),
                        "additional_time_span": DictElement(
                            required=True,
                            parameter_form=Integer(
                                title=Title(
                                    "Extend post-diagnostics phase by additional time span"
                                ),
                                unit_symbol="min",
                                prefill=DefaultValue(0),
                            ),
                        ),
                    },
                ),
            ),
            "battime": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Time left on battery"),
                    help_text=Help(
                        "Time left on Battery at and below which a warning/critical state is triggered"
                    ),
                    form_spec_template=TimeSpan(
                        title=Title("Age"),
                        displayed_magnitudes=[TimeMagnitude.HOUR, TimeMagnitude.MINUTE],
                    ),
                    level_direction=LevelDirection.LOWER,
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                    prefill_fixed_levels=DefaultValue((0.0, 0.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
            "battery_replace_state": DictElement(
                required=False,
                parameter_form=ServiceState(
                    title=Title("State if battery needs replacement"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
        }
    )


rule_spec_apc_symentra = CheckParameters(
    name="apc_symentra",
    title=Title("APC Symmetra Checks"),
    topic=Topic.ENVIRONMENTAL,
    parameter_form=_parameter_valuespec_apc_symentra,
    condition=HostCondition(),
)
