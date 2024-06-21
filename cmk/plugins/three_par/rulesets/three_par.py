#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.plugins.three_par.lib.special_agent import DEFAULT_VALUES, VALID_VALUES
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    migrate_to_password,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _migrate_values(params: object) -> Mapping[str, object]:
    match params:
        case {"values": list(values), **rest}:
            return {
                "values": [v for v in values if v in VALID_VALUES],
                **{str(k): v for k, v in rest.items()},
            }
        case dict():
            return {**params, "values": list(DEFAULT_VALUES)}
    raise ValueError(f"Invalid parameters: {params!r}")


def _form_special_agents_3par() -> Dictionary:
    return Dictionary(
        title=Title("3PAR configuration"),
        elements={
            "user": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Password"),
                    migrate=migrate_to_password,
                ),
                required=True,
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("TCP port number"),
                    help_text=Help("Port number that 3par is listening on. The default is 8080."),
                    custom_validate=(validators.NetworkPort(),),
                    prefill=DefaultValue(8080),
                ),
                required=True,
            ),
            "verify_cert": DictElement(
                parameter_form=BooleanChoice(
                    label=Label("SSL certificate verification"),
                ),
                required=True,
            ),
            "values": DictElement(
                required=True,
                parameter_form=MultipleChoice(
                    title=Title("Values to fetch"),
                    elements=[
                        MultipleChoiceElement(name=name, title=title)
                        for name, title in VALID_VALUES.items()
                    ],
                    prefill=DefaultValue(list(DEFAULT_VALUES)),
                ),
            ),
        },
        migrate=_migrate_values,
    )


rule_spec_three_par = SpecialAgent(
    name="three_par",
    title=Title("3PAR configuration"),
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_form_special_agents_3par,
)
