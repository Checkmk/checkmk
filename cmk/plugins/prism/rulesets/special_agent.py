#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    migrate_to_password,
    Password,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NetworkPort
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _form_spec() -> Dictionary:
    def _pre_24_to_formspec_migration(values: object) -> dict:
        assert isinstance(values, dict)
        if "no_cert_check" not in values:
            values["no_cert_check"] = False
        return values

    return Dictionary(
        migrate=_pre_24_to_formspec_migration,
        elements={
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("TCP port for connection"),
                    custom_validate=(NetworkPort(),),
                    prefill=DefaultValue(9440),
                ),
                required=False,
            ),
            "username": DictElement(
                parameter_form=String(title=Title("User ID for web login")),
                required=True,
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Password of the user"),
                    custom_validate=(LengthInRange(min_value=1),),
                    migrate=migrate_to_password,
                ),
                required=True,
            ),
            "no_cert_check": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Skip TLS certificate verification"),
                    prefill=DefaultValue(False),
                ),
                required=True,
            ),
            "timeout": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Connection timeout"),
                    displayed_magnitudes=(TimeMagnitude.SECOND,),
                    prefill=InputHint(10.0),
                ),
            ),
        },
    )


rule_spec_special_agent_prism = SpecialAgent(
    topic=Topic.OPERATING_SYSTEM,
    name="prism",
    title=Title("Nutanix Prism"),
    parameter_form=_form_spec,
)
