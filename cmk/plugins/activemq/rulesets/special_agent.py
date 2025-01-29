#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    migrate_to_password,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "servername": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Server Name"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "port": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Port Number"),
                    prefill=DefaultValue(8161),
                    custom_validate=(validators.NetworkPort(),),
                ),
            ),
            "protocol": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Protocol"),
                    elements=[
                        SingleChoiceElement("http", Title("HTTP")),
                        SingleChoiceElement("https", Title("HTTPS")),
                    ],
                    prefill=DefaultValue("http"),
                ),
            ),
            "use_piggyback": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Use Piggyback"),
                    label=Label("Enable"),
                ),
            ),
            "basicauth": DictElement(
                parameter_form=Dictionary(
                    migrate=_migrate_basicauth,
                    title=Title("BasicAuth settings"),
                    elements={
                        "username": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Username"),
                            ),
                        ),
                        "password": DictElement(
                            required=True,
                            parameter_form=Password(
                                title=Title("Password"),
                                migrate=migrate_to_password,
                            ),
                        ),
                    },
                ),
            ),
        },
    )


rule_spec_special_agent_activemq = SpecialAgent(
    name="activemq",
    title=Title("Apache ActiveMQ queues"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form,
)


def _migrate_basicauth(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    assert isinstance(value, tuple)
    return {
        "username": value[0],
        "password": value[1],
    }
