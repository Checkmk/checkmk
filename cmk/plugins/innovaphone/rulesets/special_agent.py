#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
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
        migrate=_migrate,
        help_text=Help("Please specify the user and password needed to access the xml interface"),
        elements={
            "protocol": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Protocol"),
                    elements=[
                        SingleChoiceElement("http", Title("HTTP")),
                        SingleChoiceElement("https", Title("HTTPS")),
                    ],
                ),
            ),
            "cert_verification": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("TLS certificate verification"),
                    help_text=Help("Verify TLS certificate (not verifying is insecure)"),
                    prefill=DefaultValue(True),
                ),
            ),
            "auth_basic": DictElement(
                required=True,
                parameter_form=Dictionary(
                    title=Title("Basic authentication"),
                    elements={
                        "username": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Login username"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
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


rule_spec_special_agent_innovaphone = SpecialAgent(
    name="innovaphone",
    title=Title("Innovaphone Gateways"),
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_parameter_form,
)


def _migrate(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(value)
    if "cert_verification" in value:
        return value
    return {k: v for k, v in value.items() if k != "no-cert-check"} | {
        "cert_verification": not value.get("no-cert-check", False)
    }
