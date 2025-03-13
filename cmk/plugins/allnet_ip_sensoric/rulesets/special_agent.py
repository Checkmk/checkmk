#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _migrate_to_float(value: object) -> float:
    match value:
        case float() | int():
            return float(value)
    raise ValueError(f"Invalid value: {value!r}")


def parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("ALLNET IP Sensoric Devices"),
        help_text=Help(
            "This rule selects the ALLNET IP Sensoric agent, which fetches "
            "/xml/sensordata.xml from the device by HTTP and extracts the "
            "needed monitoring information from this file."
        ),
        elements={
            "timeout": DictElement(
                required=False,
                parameter_form=TimeSpan(
                    title=Title("Connect timeout"),
                    help_text=Help(
                        "The network timeout in seconds when communicating via HTTP. "
                        "The default is 10 seconds."
                    ),
                    prefill=DefaultValue(10.0),
                    custom_validate=(
                        validators.NumberInRange(
                            min_value=1, error_msg=Message("The timeout must be at least 1 second.")
                        ),
                    ),
                    displayed_magnitudes=[TimeMagnitude.SECOND],
                    migrate=_migrate_to_float,
                ),
            )
        },
    )


rule_spec_special_agent_allnet_ip_sensoric = SpecialAgent(
    name="allnet_ip_sensoric",
    title=Title("ALLNET IP Sensoric Devices"),
    topic=Topic.GENERAL,
    parameter_form=parameter_form,
)
