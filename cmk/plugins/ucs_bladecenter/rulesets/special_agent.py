#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    migrate_to_password,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("UCS Bladecenter"),
        help_text=Help(
            "This rule selects the UCS Bladecenter agent instead of the normal Checkmk Agent "
            "which collects the data through the UCS Bladecenter Web API"
        ),
        elements={
            "username": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Password"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    migrate=migrate_to_password,
                ),
            ),
            "certificate_validation": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Enable TLS certificate validation"),
                    prefill=DefaultValue(True),
                ),
            ),
        },
        migrate=migrate_cert_check,
    )


def migrate_cert_check(params: object) -> Mapping[str, object]:
    if not isinstance(params, dict):
        raise TypeError(f"Invalid parameters: {params!r}")
    return {
        "username": params["username"],
        "password": params["password"],
        "certificate_validation": params.get(
            "certificate_validation",
            not params.get("no-cert-check", False),
        ),
    }


rule_spec_special_agent_ucs_bladecenter = SpecialAgent(
    name="ucs_bladecenter",
    title=Title("UCS Bladecenter"),
    topic=Topic.GENERAL,
    parameter_form=_parameter_form,
)
