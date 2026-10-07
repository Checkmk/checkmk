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


def _cartridge_flag_state(title: Title) -> DictElement[Literal[0, 1, 2, 3]]:
    return DictElement(
        required=False,
        parameter_form=ServiceState(title=title, prefill=DefaultValue(ServiceState.WARN)),
    )


def _parameter_valuespec_apc_symmetra() -> Dictionary:
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
                        "Time left on battery at and below which a WARNING/CRITICAL state is triggered"
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
            "cartridge_flag_states": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("States of battery pack cartridge flags"),
                    help_text=Help(
                        "Some UPS models report status flags for each battery pack cartridge. "
                        "A cartridge is reported with the worst state of the flags it has set. "
                        "Flags not configured here result in a WARNING state. The flag "
                        "<i>Needs Replacement</i> follows the option "
                        "<i>State if battery needs replacement</i>."
                    ),
                    elements={
                        "disconnected": _cartridge_flag_state(
                            Title("State for <i>Disconnected</i>")
                        ),
                        "overvoltage": _cartridge_flag_state(Title("State for <i>Overvoltage</i>")),
                        "overtemperature_critical": _cartridge_flag_state(
                            Title("State for <i>Overtemperature Critical</i>")
                        ),
                        "charger": _cartridge_flag_state(Title("State for <i>Charger</i>")),
                        "temperature_sensor": _cartridge_flag_state(
                            Title("State for <i>Temperature Sensor</i>")
                        ),
                        "bus_soft_start": _cartridge_flag_state(
                            Title("State for <i>Bus Soft Start</i>")
                        ),
                        "overtemperature_warning": _cartridge_flag_state(
                            Title("State for <i>Overtemperature Warning</i>")
                        ),
                        "general_error": _cartridge_flag_state(
                            Title("State for <i>General Error</i>")
                        ),
                        "communication": _cartridge_flag_state(
                            Title("State for <i>Communication</i>")
                        ),
                        "disconnected_frame": _cartridge_flag_state(
                            Title("State for <i>Disconnected Frame</i>")
                        ),
                        "firmware_mismatch": _cartridge_flag_state(
                            Title("State for <i>Firmware Mismatch</i>")
                        ),
                    },
                ),
            ),
        }
    )


rule_spec_apc_symmetra = CheckParameters(
    name="apc_symmetra",
    title=Title("APC Symmetra Checks"),
    topic=Topic.ENVIRONMENTAL,
    parameter_form=_parameter_valuespec_apc_symmetra,
    condition=HostCondition(),
)
