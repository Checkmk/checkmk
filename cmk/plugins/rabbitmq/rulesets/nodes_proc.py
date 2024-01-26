#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    Percentage,
    SimpleLevels,
    SimpleLevelsConfigModel,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_rabbitmq_nodes_proc() -> Dictionary:
    fd_perc = CascadingSingleChoiceElement[SimpleLevelsConfigModel[float]](
        name="fd_perc",
        title=Title("Percentual levels for used processes"),
        parameter_form=SimpleLevels[float](
            level_direction=LevelDirection.UPPER,
            form_spec_template=Percentage(),
            prefill_fixed_levels=DefaultValue(value=(80.0, 90.0)),
            migrate=migrate_to_float_simple_levels,
        ),
    )
    fd_abs = CascadingSingleChoiceElement[SimpleLevelsConfigModel[int]](
        name="fd_abs",
        title=Title("Absolute levels for total number of used processes"),
        parameter_form=SimpleLevels[int](
            level_direction=LevelDirection.UPPER,
            form_spec_template=Integer(label=Label("number of processes")),
            prefill_fixed_levels=InputHint(value=(0, 0)),
            migrate=migrate_to_integer_simple_levels,
        ),
    )

    return Dictionary(
        elements={
            "levels": DictElement[tuple[str, object]](
                parameter_form=CascadingSingleChoice(
                    title=Title("Levels for erlang process usage"),
                    elements=[fd_perc, fd_abs],
                    prefill=DefaultValue("fd_perc"),
                )
            )
        },
    )


rule_spec_rabbitmq_nodes_proc = CheckParameters(
    name="rabbitmq_nodes_proc",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_rabbitmq_nodes_proc,
    title=Title("RabbitMQ nodes processes"),
    condition=HostAndItemCondition(item_title=Title("Node name")),
)
