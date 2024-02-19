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
    Integer,
    Percentage,
    TupleDoNotUseWillbeRemoved,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_rabbitmq_nodes_proc() -> Dictionary:
    fd_perc = CascadingSingleChoiceElement(
        name="fd_perc",
        title=Title("Percentual levels for used processes"),
        parameter_form=TupleDoNotUseWillbeRemoved(
            elements=[
                Percentage(title=Title("Warning at usage of")),  # prefill_value=80.0),
                Percentage(title=Title("Critical at usage of")),  # prefill_value=90.0),
            ],
        ),
    )
    fd_abs = CascadingSingleChoiceElement(
        name="fd_abs",
        title=Title("Absolute levels for total number of used processes"),
        parameter_form=TupleDoNotUseWillbeRemoved(
            elements=[
                Integer(title=Title("Warning at"), unit=Label("processes")),
                Integer(title=Title("Critical at"), unit=Label("processes")),
            ],
        ),
    )

    return Dictionary(
        elements={
            "levels": DictElement(
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
