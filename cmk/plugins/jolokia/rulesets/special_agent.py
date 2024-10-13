#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
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
from cmk.rulesets.v1.form_specs._basic import FieldSize
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Jolokia"),
        help_text=Help("This rule allows querying the Jolokia web API."),
        elements={
            "port": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("TCP port for connection"),
                    prefill=DefaultValue(8080),
                    custom_validate=(validators.NetworkPort(),),
                ),
            ),
            "login": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Optional login (if required)"),
                    elements={
                        "user": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("User ID for web login (if login required)"),
                                prefill=DefaultValue("monitoring"),
                            ),
                        ),
                        "password": DictElement(
                            required=True,
                            parameter_form=Password(
                                title=Title("Password for this user"),
                                migrate=migrate_to_password,
                            ),
                        ),
                        "mode": DictElement(
                            required=True,
                            parameter_form=SingleChoice(
                                title=Title("Login mode"),
                                elements=[
                                    SingleChoiceElement(
                                        name="basic", title=Title("HTTP Basic Authentication")
                                    ),
                                    SingleChoiceElement(name="digest", title=Title("HTTP Digest")),
                                ],
                            ),
                        ),
                    },
                    migrate=_migrate_tuple_to_dict,
                ),
            ),
            "suburi": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("relative URI under which Jolokia is visible"),
                    prefill=DefaultValue("jolokia"),
                    field_size=FieldSize.MEDIUM,
                ),
            ),
            "instance": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Name of the instance in the monitoring"),
                    help_text=Help(
                        "If you do not specify a name here, "
                        "then the TCP port number will be used as an instance name."
                    ),
                ),
            ),
            "protocol": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Protocol"),
                    elements=[
                        SingleChoiceElement(name="http", title=Title("HTTP")),
                        SingleChoiceElement(name="https", title=Title("HTTPS")),
                    ],
                ),
            ),
        },
    )


def _migrate_tuple_to_dict(param: object) -> Mapping[str, object]:
    match param:
        case (user_id, password, login_mode):
            return {
                "user": user_id,
                "password": password,
                "mode": login_mode,
            }
        case dict() as already_migrated:
            return already_migrated
    raise ValueError(param)


rule_spec_special_agent_jolokia = SpecialAgent(
    name="jolokia",
    title=Title("Jolokia"),
    topic=Topic.APPLICATIONS,
    parameter_form=parameter_form,
)
