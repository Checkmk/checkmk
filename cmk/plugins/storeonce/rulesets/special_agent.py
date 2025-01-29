#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DictElement,
    Dictionary,
    migrate_to_password,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.form_specs._base import DefaultValue
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("HPE StoreOnce"),
        elements={
            "user": DictElement(
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
            "ignore_tls": DictElement(
                parameter_form=BooleanChoice(
                    label=Label("Ignore TLS certificate"),
                    prefill=DefaultValue(False),
                ),
                required=True,
            ),
        },
        migrate=_migrate_cert,
    )


def _migrate_cert(params: object) -> Mapping[str, object]:
    match params:
        case {"cert": cert_value, **rest}:
            return {
                "ignore_tls": cert_value,
                **{str(k): v for k, v in rest.items()},
            }
        case dict():
            return {**params, "ignore_tls": False}
    raise ValueError(f"Invalid parameters: {params!r}")


rule_spec_special_agent_storeonce = SpecialAgent(
    name="storeonce",
    title=Title("HPE StoreOnce"),
    topic=Topic.GENERAL,
    parameter_form=parameter_form,
)
