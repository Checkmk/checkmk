#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import (
    CascadingDropdown,
    CascadingDropdownElement,
    CheckParameterRuleSpecWithItem,
    DictElement,
    Dictionary,
    Integer,
    Localizable,
    Percentage,
    RuleSpecSubGroup,
    TextInput,
    Tuple,
)


def _parameter_valuespec_rabbitmq_nodes_proc():
    fd_perc = CascadingDropdownElement(
        ident="fd_perc",
        value_spec=Tuple(
            title=Localizable("Percentual levels for used processes"),
            elements=[
                Percentage(title=Localizable("Warning at usage of"), default_value=80.0),
                Percentage(title=Localizable("Critical at usage of"), default_value=90.0),
            ],
        ),
    )
    fd_abs = CascadingDropdownElement(
        ident="fd_abs",
        value_spec=Tuple(
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
                spec=CascadingDropdown(
                    title=Localizable("Levels for erlang process usage"),
                    elements=[fd_perc, fd_abs],
                    default_element="fd_perc",
                )
            )
        }
    )


rulespec_rabbitmq_nodes_proc = CheckParameterRuleSpecWithItem(
    name="rabbitmq_nodes_proc",
    group=RuleSpecSubGroup.CHECK_PARAMETERS_APPLICATIONS,
    item=TextInput(title=Localizable("Node name")),
    value_spec=_parameter_valuespec_rabbitmq_nodes_proc,
    title=Localizable("RabbitMQ nodes processes"),
)
