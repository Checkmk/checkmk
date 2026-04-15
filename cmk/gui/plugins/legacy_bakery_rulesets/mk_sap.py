#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    List,
    migrate_to_password,
    Password,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate_instance(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Unexpected value: {value!r}")
    return {**value, "passwd": migrate_to_password(value["passwd"])}


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "deployment" in value:
        return value
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    if isinstance(value, dict):
        return {"deployment": ("sync", None), **value}
    raise ValueError(f"Unexpected value: {value!r}")


def _instance_form() -> Dictionary:
    return Dictionary(
        title=Title("SAP R/3 instance"),
        migrate=migrate_instance,
        elements={
            "ashost": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Host name"),
                    prefill=DefaultValue("localhost"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "sysnr": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("System Number"),
                    prefill=DefaultValue("00"),
                    custom_validate=(validators.MatchRegex(r"^[0-9][0-9]$"),),
                ),
            ),
            "client": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("SAP-Client"),
                    prefill=DefaultValue("100"),
                    custom_validate=(validators.MatchRegex(r"^[0-9]{3}$"),),
                ),
            ),
            "user": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("User for login"),
                    prefill=DefaultValue("cmk-user"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "passwd": DictElement(
                required=True,
                parameter_form=Password(title=Title("Password for login")),
            ),
            "trace": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Trace level"),
                    prefill=DefaultValue("3"),
                    custom_validate=(validators.MatchRegex(r"^[1-9]$"),),
                ),
            ),
            "lang": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Language"),
                    prefill=DefaultValue("EN"),
                    custom_validate=(validators.MatchRegex(r"^[A-Z][A-Z]$"),),
                ),
            ),
            "host_prefix": DictElement(
                parameter_form=String(
                    title=Title("Prefix for piggyback host name"),
                ),
            ),
        },
    )


def _valuespec_agent_config_mk_sap() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This rule set will deploy the agent plug-in <tt>mk_sap</tt> for (locally) monitoring "
            "SAP R/3 instances. Note: you still need to manually deploy the SAP NetWeaver RFCSDK "
            "(nwrfcsdk) and the Python module sapnwrfc."
        ),
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy the plug-in and run it synchronously"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="cached",
                            title=Title("Deploy the plug-in and run it asynchronously"),
                            parameter_form=TimeSpan(
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy the SAP R/3 plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
            "instances": DictElement(
                parameter_form=List(
                    title=Title("Instances to monitor"),
                    add_element_label=Label("Add instance to monitor"),
                    element_template=_instance_form(),
                ),
            ),
            "paths": DictElement(
                parameter_form=List(
                    title=Title("CCMS paths to monitor"),
                    help_text=Help(
                        "Specify the paths in CCMS that you want to monitor. Each entry must match"
                        " the full path to one or several monitor objects. Unix shell patterns are"
                        " supported: * matches everything, ? matches any single character,"
                        " [seq] matches any character in seq, [!seq] matches any character not in seq."
                        " If left empty, the following default paths are used:"
                        " SAP BI Monitors/BI Monitor,"
                        " SAP BI Monitors/BI Monitor/*/Oracle/Performance,"
                        " SAP CCMS Monitor Templates/Operating System/OperatingSystem/CPU/*,"
                        " SAP CCMS Monitor Templates/Operating System/OperatingSystem/CPU/CPU_Utilization."
                    ),
                    element_template=String(),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_mk_sap = AgentConfig(
    title=Title("SAP R/3 monitoring plug-in"),
    name="mk_sap",
    topic=Topic.APPLICATIONS,
    parameter_form=_valuespec_agent_config_mk_sap,
)
