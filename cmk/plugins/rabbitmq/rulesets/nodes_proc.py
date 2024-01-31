#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Localizable
from cmk.rulesets.v1.form_specs.basic import Integer, Percentage, Text
from cmk.rulesets.v1.form_specs.composed import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DictElement,
    Dictionary,
    TupleDoNotUseWillbeRemoved,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_rabbitmq_nodes_proc() -> Dictionary:
    fd_perc = CascadingSingleChoiceElement(
        name="fd_perc",
        title=Localizable("Percentual levels for used processes"),
        parameter_form=TupleDoNotUseWillbeRemoved(
            title=Localizable("Percentual levels for used processes"),
            elements=[
                Percentage(title=Localizable("Warning at usage of"), prefill_value=80.0),
                Percentage(title=Localizable("Critical at usage of"), prefill_value=90.0),
            ],
        ),
    )
    fd_abs = CascadingSingleChoiceElement(
        name="fd_abs",
        title=Localizable("Absolute levels for total number of used processes"),
        parameter_form=TupleDoNotUseWillbeRemoved(
            title=Localizable("Absolute levels for total number of used processes"),
            elements=[
                Integer(title=Localizable("Warning at"), unit=Localizable("processes")),
                Integer(title=Localizable("Critical at"), unit=Localizable("processes")),
            ],
        ),
    )

    return Dictionary(
        elements={
            "levels": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Localizable("Levels for erlang process usage"),
                    elements=[fd_perc, fd_abs],
                    prefill_selection="fd_perc",
                )
            )
        },
    )


rule_spec_rabbitmq_nodes_proc = CheckParameters(
    name="rabbitmq_nodes_proc",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_rabbitmq_nodes_proc,
    title=Localizable("RabbitMQ nodes processes"),
    condition=HostAndItemCondition(item_form=Text(title=Localizable("Node name"))),
)
