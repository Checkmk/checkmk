#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    migrate_to_password,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Ruckus Spot"),
        help_text=Help(
            "This rule selects the Agent Ruckus Spot agent instead of the normal Checkmk Agent "
            "which collects the data through the Ruckus Spot web interface"
        ),
        elements={
            "address": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Server Address"),
                    help_text=Help(
                        "Here you can set a manual address if the server differs from the host"
                    ),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="use_host_address",
                            title=Title("Use host address"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="manual_address",
                            title=Title("Enter address"),
                            parameter_form=String(
                                title=Title("Enter address"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                        ),
                    ],
                    prefill=DefaultValue("use_host_address"),
                    migrate=_migrate_address,
                ),
            ),
            "port": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Port"),
                    prefill=DefaultValue(8443),
                    custom_validate=(validators.NetworkPort(),),
                ),
            ),
            "venueid": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Venue ID"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "api_key": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("API key"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    migrate=migrate_to_password,
                ),
            ),
            "cmk_agent": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Also contact Checkmk agent"),
                    help_text=Help(
                        "With this setting, the special agent will also contact the "
                        "Checkmk agent on the same system at the specified port."
                    ),
                    elements={
                        "port": DictElement(
                            required=True,
                            parameter_form=Integer(
                                title=Title("Port"),
                                prefill=DefaultValue(6556),
                                custom_validate=(validators.NetworkPort(),),
                            ),
                        )
                    },
                ),
            ),
        },
    )


def _migrate_address(
    value: object,
) -> tuple[Literal["use_host_address"], None] | tuple[Literal["manual_address"], str]:
    match value:
        case tuple() as already_migrated:
            return already_migrated
        case str() as address:
            return ("manual_address", address)
        case bool():
            return ("use_host_address", None)
        case _:
            raise TypeError(value)


rule_spec_special_agent_ruckus_spot = SpecialAgent(
    name="ruckus_spot",
    title=Title("Ruckus Spot"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form,
)
