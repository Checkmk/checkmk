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
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_valuespec_graylog_sidecars() -> Dictionary:
    return Dictionary(
        elements={
            "active_state": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when active state is not OK"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "last_seen": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Time since the sidecar was last seen by Graylog"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=[
                            TimeMagnitude.DAY,
                            TimeMagnitude.HOUR,
                            TimeMagnitude.MINUTE,
                            TimeMagnitude.SECOND,
                        ],
                    ),
                    prefill_fixed_levels=InputHint((0.0, 0.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
            "running_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of collectors in state running lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="collectors"),
                    prefill_fixed_levels=DefaultValue((1, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "running_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of collectors in state running upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="collectors"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "stopped_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of collectors in state stopped lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="collectors"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "stopped_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of collectors in state stopped upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="collectors"),
                    prefill_fixed_levels=DefaultValue((1, 1)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "failing_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of collectors in state failing lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="collectors"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "failing_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total number of collectors in state failing upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="collectors"),
                    prefill_fixed_levels=DefaultValue((1, 1)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "running": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when collector is in state running"),
                    prefill=DefaultValue(ServiceState.OK),
                ),
            ),
            "stopped": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when collector is in state stopped"),
                    prefill=DefaultValue(ServiceState.WARN),
                ),
            ),
            "failing": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when collector is in state failing"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
            "no_ping": DictElement(
                parameter_form=ServiceState(
                    title=Title("State when no ping signal from sidecar"),
                    prefill=DefaultValue(ServiceState.CRIT),
                ),
            ),
        },
    )


rule_spec_graylog_sidecars = CheckParameters(
    name="graylog_sidecars",
    title=Title("Graylog sidecars"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_valuespec_graylog_sidecars,
    condition=HostAndItemCondition(item_title=Title("Sidecar name")),
)
