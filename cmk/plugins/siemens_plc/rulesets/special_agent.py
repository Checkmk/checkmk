#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Mapping, Sequence

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Float,
    Integer,
    List,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This rule selects the Siemens PLC agent instead of the normal Checkmk Agent "
            "and allows monitoring of Siemens PLC using the Snap7 API. You can configure "
            "your connection settings and values to fetch here."
        ),
        elements={
            "devices": DictElement(
                required=True,
                parameter_form=List(
                    title=Title("Devices to fetch information from"),
                    element_template=Dictionary(
                        elements={
                            "host_name": DictElement(
                                required=True,
                                parameter_form=String(
                                    title=Title("Name of the PLC"),
                                    custom_validate=(validators.LengthInRange(min_value=1),),
                                    help_text=Help(
                                        "Specify the logical name, e.g. the host name, of the PLC. This name "
                                        "is used to name the resulting services."
                                    ),
                                ),
                            ),
                            "host_address": DictElement(
                                required=True,
                                parameter_form=String(
                                    title=Title("Network address"),
                                    custom_validate=(validators.LengthInRange(min_value=1),),
                                    help_text=Help(
                                        "Specify the host name or IP address of the PLC to communicate with."
                                    ),
                                ),
                            ),
                            "rack": DictElement(
                                required=True,
                                parameter_form=Integer(
                                    title=Title("Number of the Rack"),
                                    custom_validate=(validators.NumberInRange(min_value=0),),
                                ),
                            ),
                            "slot": DictElement(
                                required=True,
                                parameter_form=Integer(
                                    title=Title("Number of the Slot"),
                                    custom_validate=(validators.NumberInRange(min_value=0),),
                                ),
                            ),
                            "tcp_port": DictElement(
                                required=True,
                                parameter_form=Integer(
                                    title=Title("TCP Port number"),
                                    help_text=Help("Port number for communicating with the PLC"),
                                    prefill=DefaultValue(102),
                                    custom_validate=(validators.NetworkPort(),),
                                ),
                            ),
                            "values": DictElement(
                                required=True,
                                parameter_form=List(
                                    title=Title("Values to fetch from this device"),
                                    element_template=Dictionary(
                                        elements=_value_configuration_fields(),
                                        migrate=_migrate_value_entry,
                                    ),
                                    custom_validate=(_validate_values,),
                                ),
                            ),
                        },
                    ),
                ),
            ),
            "values": DictElement(
                required=True,
                parameter_form=List(
                    title=Title("Values to fetch from all devices"),
                    element_template=Dictionary(
                        elements=_value_configuration_fields(),
                        migrate=_migrate_value_entry,
                    ),
                    custom_validate=(_validate_values,),
                ),
            ),
            "timeout": DictElement(
                parameter_form=Integer(
                    title=Title("Connect timeout"),
                    help_text=Help(
                        "The connect timeout in seconds when establishing a connection "
                        "with the PLC."
                    ),
                    prefill=DefaultValue(10),
                    custom_validate=(validators.NumberInRange(min_value=1),),
                    unit_symbol="s",
                ),
            ),
        },
    )


rule_spec_special_agent_siemens_plc = SpecialAgent(
    name="siemens_plc",
    title=Title("Siemens PLC (SPS)"),
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_parameter_form,
)


def _value_configuration_fields() -> dict[str, DictElement]:
    return {
        "area": DictElement(
            required=True,
            parameter_form=CascadingSingleChoice(
                title=Title("The Area"),
                prefill=DefaultValue("db"),
                elements=[
                    CascadingSingleChoiceElement(
                        name="db",
                        title=Title("Datenbaustein"),
                        parameter_form=Integer(
                            title=Title("DB Number"),
                            custom_validate=(validators.NumberInRange(min_value=1),),
                            prefill=DefaultValue(1),
                        ),
                    ),
                    CascadingSingleChoiceElement(
                        name="input",
                        title=Title("Input"),
                        parameter_form=FixedValue(value=None),
                    ),
                    CascadingSingleChoiceElement(
                        name="output",
                        title=Title("Output"),
                        parameter_form=FixedValue(value=None),
                    ),
                    CascadingSingleChoiceElement(
                        name="merker",
                        title=Title("Merker"),
                        parameter_form=FixedValue(value=None),
                    ),
                    CascadingSingleChoiceElement(
                        name="timer",
                        title=Title("Timer"),
                        parameter_form=FixedValue(value=None),
                    ),
                    CascadingSingleChoiceElement(
                        name="counter",
                        title=Title("Counter"),
                        parameter_form=FixedValue(value=None),
                    ),
                ],
            ),
        ),
        "address": DictElement(
            required=True,
            parameter_form=Float(
                title=Title("Address"),
                help_text=Help(
                    "Addresses are specified with a dot notation, where number "
                    "before the dot specify the byte to fetch and the number after the "
                    "dot specifies the bit to fetch. The number of the bit is always "
                    "between 0 and 7."
                ),
            ),
        ),
        "data_type": DictElement(
            required=True,
            parameter_form=CascadingSingleChoice(
                title=Title("Datatype"),
                prefill=DefaultValue("dint"),
                elements=[
                    CascadingSingleChoiceElement(
                        name="dint",
                        title=Title("Double Integer (DINT)"),
                        parameter_form=FixedValue(value=None),
                    ),
                    CascadingSingleChoiceElement(
                        name="real",
                        title=Title("Real Number (REAL)"),
                        parameter_form=FixedValue(value=None),
                    ),
                    CascadingSingleChoiceElement(
                        name="bit",
                        title=Title("Single Bit (BOOL)"),
                        parameter_form=FixedValue(value=None),
                    ),
                    CascadingSingleChoiceElement(
                        name="str",
                        title=Title("String (STR)"),
                        parameter_form=Integer(
                            title=Title("Size"),
                            unit_symbol="b",
                            custom_validate=(validators.NumberInRange(min_value=1),),
                        ),
                    ),
                    CascadingSingleChoiceElement(
                        name="raw",
                        title=Title("Raw Bytes (HEXSTR)"),
                        parameter_form=Integer(
                            title=Title("Size"),
                            unit_symbol="b",
                            custom_validate=(validators.NumberInRange(min_value=1),),
                        ),
                    ),
                ],
            ),
        ),
        "value_type": DictElement(
            required=True,
            parameter_form=SingleChoice(
                title=Title("Type of the value"),
                prefill=DefaultValue("unclassified"),
                elements=[
                    SingleChoiceElement(
                        name="unclassified",
                        title=Title("Unclassified"),
                    ),
                    SingleChoiceElement(
                        name="temp",
                        title=Title("Temperature"),
                    ),
                    SingleChoiceElement(
                        name="hours_operation",
                        title=Title("Hours of operation"),
                    ),
                    SingleChoiceElement(
                        name="hours_since_service",
                        title=Title("Hours since service"),
                    ),
                    SingleChoiceElement(
                        name="hours",
                        title=Title("Hours"),
                    ),
                    SingleChoiceElement(
                        name="seconds_operation",
                        title=Title("Seconds of operation"),
                    ),
                    SingleChoiceElement(
                        name="seconds_since_service",
                        title=Title("Seconds since service"),
                    ),
                    SingleChoiceElement(
                        name="seconds",
                        title=Title("Seconds"),
                    ),
                    SingleChoiceElement(
                        name="counter",
                        title=Title("Increasing counter"),
                    ),
                    SingleChoiceElement(
                        name="flag",
                        title=Title("State flag (on/off)"),
                    ),
                    SingleChoiceElement(
                        name="text",
                        title=Title("Text"),
                    ),
                ],
            ),
        ),
        "id": DictElement(
            required=True,
            parameter_form=String(
                title=Title("Ident of the value"),
                help_text=Help(
                    "An identifier of your choice. This identifier "
                    "is used by the Checkmk checks to access "
                    "and identify the single values. The identifier "
                    "needs to be unique within a group of VALUETYPES."
                ),
                custom_validate=(_validate_id,),
            ),
        ),
    }


def _validate_values(configured_values: Sequence[Mapping[str, object]]) -> None:
    value_types_and_ids = [(value["value_type"], value["id"]) for value in configured_values]
    if len(value_types_and_ids) != len(set(value_types_and_ids)):
        raise validators.ValidationError(
            Message("The identifiers need to be unique per value type.")
        )


def _validate_id(value: str) -> None:
    if not value:
        return
    validators.MatchRegex(
        re.compile(r"^[^\d\W][-\w]*$", re.ASCII),
        error_msg=Message(
            "An identifier must only consist of letters, digits, dash and "
            "underscore and it must start with a letter or underscore."
        ),
    )(value)


def _migrate_value_entry(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value

    # TODO: valuespec-removal: This happens in the complain phase of a valuespec
    # The ListOf valuespec creates a None out of nowhere
    # This is a workaround keep the strict typing and make the migration work
    # This returned value here, is not used anywhere
    if value is None:
        return {}

    assert isinstance(value, tuple)
    db_number, address, data_type, value_type, ident = value
    return {
        "area": db_number if isinstance(db_number, tuple) else (db_number, None),
        "address": address,
        "data_type": data_type if isinstance(data_type, tuple) else (data_type, None),
        "value_type": "unclassified" if value_type is None else value_type,
        "id": ident,
    }
