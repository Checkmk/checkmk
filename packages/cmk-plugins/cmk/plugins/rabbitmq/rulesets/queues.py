#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DictElement,
    Dictionary,
    Float,
    IECMagnitude,
    InputHint,
    Integer,
    LevelDirection,
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_rabbitmq_queues() -> Dictionary:
    return Dictionary(
        elements={
            "msg_upper": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Upper level for total number of messages"),
                    form_spec_template=Integer(unit_symbol="messages"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "msg_lower": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Lower level for total number of messages"),
                    form_spec_template=Integer(unit_symbol="messages"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "msg_ready_upper": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Upper level for total number of ready messages"),
                    form_spec_template=Integer(unit_symbol="messages"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "msg_ready_lower": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Lower level for total number of ready messages"),
                    form_spec_template=Integer(unit_symbol="messages"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "msg_unack_upper": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Upper level for total number of unacknowledged messages"),
                    form_spec_template=Integer(unit_symbol="messages"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "msg_unack_lower": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Lower level for total number of unacknowledged messages"),
                    form_spec_template=Integer(unit_symbol="messages"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "msg_publish_upper": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Upper level for total number of published messages"),
                    form_spec_template=Integer(unit_symbol="messages"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "msg_publish_lower": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Lower level for total number of published messages"),
                    form_spec_template=Integer(unit_symbol="messages"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "msg_publish_rate_upper": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Upper level for published message rate"),
                    form_spec_template=Float(unit_symbol="1/s"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint((0.0, 0.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
            "msg_publish_rate_lower": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Lower level for published message rate"),
                    form_spec_template=Float(unit_symbol="1/s"),
                    level_direction=LevelDirection.LOWER,
                    prefill_fixed_levels=InputHint((0.0, 0.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
            "abs_memory": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Absolute levels for used memory"),
                    form_spec_template=DataSize(
                        displayed_magnitudes=[
                            IECMagnitude.BYTE,
                            IECMagnitude.KIBI,
                            IECMagnitude.MEBI,
                            IECMagnitude.GIBI,
                            IECMagnitude.TEBI,
                        ]
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
        }
    )


rule_spec_rabbitmq_queues = CheckParameters(
    name="rabbitmq_queues",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_rabbitmq_queues,
    condition=HostAndItemCondition(item_title=Title("Queue name")),
    title=Title("RabbitMQ queues"),
)
