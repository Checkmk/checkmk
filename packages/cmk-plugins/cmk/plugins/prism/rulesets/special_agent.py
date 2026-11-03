#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    migrate_to_password,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NetworkPort
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _migrate(values: object) -> dict[str, object]:
    assert isinstance(values, dict)
    values.setdefault("no_cert_check", False)
    values.setdefault("api_version", "legacy")
    return values


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Note: Simultaneous monitoring of both Nutanix Prism Element "
            "and Nutanix Prism Central is not supported. "
            "Doing so may cause conflicting piggyback data."
        ),
        migrate=_migrate,
        elements={
            "api_version": DictElement(
                parameter_form=SingleChoice(
                    title=Title("API version"),
                    help_text=Help(
                        "API v4 requires Prism Central 7.3 or later managing clusters "
                        "running AOS 7.3 or later. Assign this rule to the Prism Central host."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="v4",
                            title=Title("Use API v4 (Prism Central only)"),
                        ),
                        SingleChoiceElement(
                            name="legacy",
                            title=Title("Use legacy API v1/v2 (Prism Element or Prism Central)"),
                        ),
                    ],
                    prefill=DefaultValue("v4"),
                ),
                required=True,
            ),
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
