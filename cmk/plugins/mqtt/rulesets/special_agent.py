#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.ccc.hostaddress import HostAddress

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    migrate_to_password,
    Password,
    SingleChoice,
    String,
    validators,
)
from cmk.rulesets.v1.form_specs._basic import FieldSize, SingleChoiceElement
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("MQTT broker statistics"),
        migrate=_migrate_instance_and_client_id,
        help_text=Help(
            "Connect to an MQTT broker to get statistics out of your instance. "
            "The information is fetched from the <tt>$SYS</tt> topic of the broker. The "
            "different brokers implement different topics as they are not standardized, "
            "means that not every service available with every broker. "
            "In multi-tentant, enterprise level cluster this agent may not be useful or "
            "probably only when directly connecting to single nodes, because the "
            "<tt>$SYS</tt> topic is node-specific."
        ),
        elements={
            "username": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help("The username used for broker authentication."),
                    field_size=FieldSize.MEDIUM,
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "password": DictElement(
                required=False,
                parameter_form=Password(
                    title=Title("Password of the user"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    migrate=migrate_to_password,
                ),
            ),
            "address": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Custom address"),
                    help_text=Help(
                        "When set, this address is used for connecting to the MQTT "
                        "broker. If not set, the special agent will use the primary "
                        "address of the host to connect to the MQTT broker."
                    ),
                    field_size=FieldSize.MEDIUM,
                    custom_validate=(
                        validators.LengthInRange(min_value=1),
                        _validate_hostname,
                    ),
                ),
            ),
            "port": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Port"),
                    prefill=DefaultValue(1883),
                    help_text=Help("The port that is used for the api call."),
                    custom_validate=(validators.NetworkPort(),),
                ),
            ),
            "client_id": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Client ID"),
                    help_text=Help(
                        "Unique client ID used for the broker. Will be randomly "
                        "generated when not set."
                    ),
                    field_size=FieldSize.MEDIUM,
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "protocol": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Protocol"),
                    elements=[
                        SingleChoiceElement(name="MQTTv31", title=Title("MQTTv31")),
                        SingleChoiceElement(name="MQTTv311", title=Title("MQTTv311")),
                        SingleChoiceElement(name="MQTTv5", title=Title("MQTTv5")),
                    ],
                    prefill=DefaultValue("MQTTv311"),
                ),
            ),
            "instance_id": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("Instance ID"),
                    help_text=Help(
                        "Unique ID used to identify the instance on the host within Checkmk."
                    ),
                    field_size=FieldSize.MEDIUM,
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    prefill=DefaultValue("broker"),
                ),
            ),
        },
    )


def _validate_hostname(value: str) -> None:
    try:
        HostAddress(value)
    except ValueError as exception:
        raise validators.ValidationError(
            message=Message(
                "Please enter a valid host name or IPv4 address. "
                "Only letters, digits, dash, underscore and dot are allowed."
            )
        ) from exception


def _migrate_instance_and_client_id(params: object) -> dict[str, object]:
    match params:
        case {"instance-id": instance_value, "client-id": client_value, **rest}:
            return {
                "instance_id": instance_value,
                "client_id": client_value,
                **{str(k): v for k, v in rest.items()},
            }
        case {"client-id": client_value, **rest}:
            return {
                "client_id": client_value,
                **{str(k): v for k, v in rest.items()},
            }
        case {"instance-id": instance_value, **rest}:
            return {
                "instance_id": instance_value,
                **{str(k): v for k, v in rest.items()},
            }
        case dict():
            return {**params}
    raise ValueError(f"Invalid parameters: {params!r}")


rule_spec_special_agent_mqtt = SpecialAgent(
    name="mqtt",
    title=Title("MQTT broker statistics"),
    topic=Topic.APPLICATIONS,
    parameter_form=parameter_form,
)
