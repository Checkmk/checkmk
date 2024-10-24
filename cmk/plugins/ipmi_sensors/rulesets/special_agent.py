#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
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


def _special_agents_ipmi_sensors_vs_freeipmi() -> Dictionary:
    return Dictionary(
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
            "privilege_lvl": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Privilege Level"),
                    elements=[
                        SingleChoiceElement(name="user", title=Title("USER")),
                        SingleChoiceElement(name="operator", title=Title("OPERATOR")),
                        SingleChoiceElement(name="admin", title=Title("ADMIN")),
                    ],
                    prefill=DefaultValue("operator"),
                ),
            ),
            "ipmi_driver": DictElement(
                required=False, parameter_form=String(title=Title("IPMI driver"))
            ),
            "driver_type": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("IPMI driver type"),
                    help_text=Help("Driver type to use instead of doing an auto selection"),
                ),
            ),
            "BMC_key": DictElement(
                required=False,
                parameter_form=String(
                    title=Title("BMC key"),
                    help_text=Help(
                        "K_g BMC key to use when authenticating with the remote host for IPMI 2.0"
                    ),
                ),
            ),
            "quiet_cache": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Quiet cache"),
                    label=Label("Enable"),
                    help_text=Help("Do not output information about cache creation/deletion"),
                ),
            ),
            "sdr_cache_recreate": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("SDR cache recreate"),
                    label=Label("Enable"),
                    help_text=Help("Automatically recreate the sensor data repository (SDR) cache"),
                ),
            ),
            "interpret_oem_data": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("OEM data interpretation"),
                    label=Label("Enable"),
                    help_text=Help("Attempt to interpret OEM data"),
                ),
            ),
            "output_sensor_state": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Sensor state"),
                    label=Label("Enable"),
                    prefill=DefaultValue(True),
                    help_text=Help("Output sensor state"),
                ),
            ),
            "output_sensor_thresholds": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Sensor threshold"),
                    label=Label("Enable"),
                    help_text=Help("Output sensor thresholds"),
                ),
            ),
            "ignore_not_available_sensors": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Suppress not available sensors"),
                    label=Label("Enable"),
                    help_text=Help("Ignore not-available (i.e. N/A) sensors in output"),
                ),
            ),
        },
    )


def _special_agents_ipmi_sensors_vs_ipmitool() -> Dictionary:
    return Dictionary(
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
            "privilege_lvl": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Privilege Level"),
                    elements=[
                        SingleChoiceElement(name="callback", title=Title("CALLBACK")),
                        SingleChoiceElement(name="user", title=Title("USER")),
                        SingleChoiceElement(name="operator", title=Title("OPERATOR")),
                        SingleChoiceElement(name="administrator", title=Title("ADMINISTRATOR")),
                    ],
                    prefill=DefaultValue("administrator"),
                ),
            ),
            "intf": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("IPMI Interface"),
                    help_text=Help(
                        "IPMI Interface to be used. If not specified, the default interface as set "
                        "at compile time will be used."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="open", title=Title("open - Linux OpenIPMI Interface (default)")
                        ),
                        SingleChoiceElement(name="imb", title=Title("imb - Intel IMB Interface")),
                        SingleChoiceElement(
                            name="lan", title=Title("lan - IPMI v1.5 LAN Interface")
                        ),
                        SingleChoiceElement(
                            name="lanplus", title=Title("lanplus - IPMI v2.0 RMCP+ LAN Interface")
                        ),
                    ],
                ),
            ),
        },
    )


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("IPMI Sensors via Freeipmi or IPMItool"),
        help_text=Help(
            "This rule selects the Agent IPMI Sensors instead of the normal Checkmk Agent "
            "which collects the data through the FreeIPMI resp. IPMItool command"
        ),
        elements={
            "agent": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    elements=[
                        CascadingSingleChoiceElement(
                            name="freeipmi",
                            title=Title("Use FreeIPMI"),
                            parameter_form=_special_agents_ipmi_sensors_vs_freeipmi(),
                        ),
                        CascadingSingleChoiceElement(
                            name="ipmitool",
                            title=Title("Use IPMItool"),
                            parameter_form=_special_agents_ipmi_sensors_vs_ipmitool(),
                        ),
                    ],
                ),
            )
        },
        migrate=_tuple_to_dict,
    )


def _tuple_to_dict(
    param: object,
) -> Mapping[str, object]:
    match param:
        case tuple():
            return {"agent": param}
        case dict() as already_migrated:
            return already_migrated
    raise ValueError(param)


rule_spec_special_agent_ipmi_sensors = SpecialAgent(
    name="ipmi_sensors",
    title=Title("IPMI Sensors via Freeipmi or IPMItool"),
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=_parameter_form,
)
