#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    migrate_to_float_simple_levels,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _migrate_stratum_levels(
    value: object,
) -> tuple[Literal["fixed"], tuple[int, int]] | tuple[Literal["no_levels"], None]:
    # Released as a single "critical at stratum" integer; use it as the
    # critical level and one stratum below it as the warning level, matching
    # the previous check behaviour.
    match value:
        case int():
            return ("fixed", (value - 1, value))
        case ("fixed", (int(warn), int(crit))):
            return ("fixed", (warn, crit))
        case ("no_levels", None):
            return ("no_levels", None)
        case _:
            raise TypeError(value)


def _migrate_ms_levels_to_seconds(
    value: object,
) -> tuple[Literal["fixed"], tuple[float, float]] | tuple[Literal["no_levels"], None]:
    # Released as a bare "(warn, crit)" tuple in milliseconds.
    return migrate_to_float_simple_levels(value, scale=0.001)


def _parameter_valuespec_timesyncd_time() -> Dictionary:
    return Dictionary(
        elements={
            "stratum_level": DictElement(
                required=False,
                parameter_form=SimpleLevels[int](
                    title=Title("Stratum"),
                    help_text=Help(
                        "The stratum (distance in hops to the reference clock) of the time source."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue((9, 10)),
                    migrate=_migrate_stratum_levels,
                ),
            ),
            "quality_levels": DictElement(
                required=False,
                parameter_form=SimpleLevels[float](
                    title=Title("Thresholds for quality of time"),
                    help_text=Help("The deviation of the local clock from the time server."),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(displayed_magnitudes=[TimeMagnitude.MILLISECOND]),
                    prefill_fixed_levels=DefaultValue((0.2, 0.5)),
                    migrate=_migrate_ms_levels_to_seconds,
                ),
            ),
            "alert_delay": DictElement(
                required=False,
                parameter_form=SimpleLevels[float](
                    title=Title("Phases without synchronization"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.HOUR, TimeMagnitude.MINUTE]
                    ),
                    prefill_fixed_levels=DefaultValue((300.0, 3600.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
            "last_synchronized": DictElement(
                required=False,
                parameter_form=SimpleLevels[float](
                    title=Title("Allowed duration since last synchronization"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.HOUR, TimeMagnitude.MINUTE]
                    ),
                    prefill_fixed_levels=DefaultValue((7500.0, 10800.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
            "last_ntp_message": DictElement(
                required=False,
                parameter_form=SimpleLevels[float](
                    title=Title("Allowed duration since last NTPMessage"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[TimeMagnitude.HOUR, TimeMagnitude.MINUTE]
                    ),
                    prefill_fixed_levels=DefaultValue((3600.0, 7200.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
        },
    )


rule_spec_timesyncd_time = CheckParameters(
    name="timesyncd_time",
    title=Title("Systemd timesyncd time synchronization"),
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=_parameter_valuespec_timesyncd_time,
    condition=HostCondition(),
)
