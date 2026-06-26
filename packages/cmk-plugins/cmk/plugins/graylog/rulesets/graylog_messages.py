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
    migrate_to_integer_simple_levels,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_valuespec_graylog_messages() -> Dictionary:
    return Dictionary(
        elements={
            "msgs_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total message count upper levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "msgs_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Total message count lower levels"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "msgs_avg": DictElement(
                parameter_form=Integer(
                    title=Title("Message averaging"),
                    help_text=Help(
                        "By activating averaging, Checkmk will compute the average of "
                        "the message count over a given interval. If you define "
                        "alerting levels then these will automatically be applied on the "
                        "averaged value. This helps to mask out short peaks. "
                    ),
                    unit_symbol="minutes",
                    custom_validate=(validators.NumberInRange(min_value=1),),
                    prefill=DefaultValue(30),
                ),
            ),
            "msgs_avg_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Average message count upper levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "msgs_avg_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Average message count lower levels"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "msgs_diff": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Time span for difference calculation of total number of messages"),
                    displayed_magnitudes=[
                        TimeMagnitude.DAY,
                        TimeMagnitude.HOUR,
                        TimeMagnitude.MINUTE,
                    ],
                    prefill=DefaultValue(1800.0),
                ),
            ),
            "msgs_diff_lower": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Number of messages in defined time span lower level"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(unit_symbol="messages"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "msgs_diff_upper": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Number of messages in defined time span upper level"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="messages"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        },
    )


rule_spec_graylog_messages = CheckParameters(
    name="graylog_messages",
    title=Title("Graylog messages"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_valuespec_graylog_messages,
    condition=HostCondition(),
)
