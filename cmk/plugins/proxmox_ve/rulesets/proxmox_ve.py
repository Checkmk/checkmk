#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
    FixedValue,
    Integer,
    migrate_to_password,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _migrate_element_names(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError("Invalid value {value} for Proxmox VE")

    if "no-cert-check" in value:
        value["no_cert_check"] = value.pop("no-cert-check")

    if "log-cutoff-weeks" in value:
        value["log_cutoff_weeks"] = value.pop("log-cutoff-weeks")

    return value


def _form_special_agents_proxmox_ve() -> Dictionary:
    return Dictionary(
        elements={
            "username": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                )
            ),
            "password": DictElement(
                parameter_form=Password(title=Title("Password"), migrate=migrate_to_password)
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("Port"),
                    prefill=DefaultValue(8006),
                    custom_validate=(validators.NetworkPort(),),
                )
            ),
            # copied from cisco/cisco_prime
            "host": DictElement(
                parameter_form=CascadingSingleChoice(
                    elements=[
                        CascadingSingleChoiceElement(
                            name="ip_address",
                            title=Title("IP address"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="host_name",
                            title=Title("Host name"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="custom",
                            title=Title("Custom host"),
                            parameter_form=String(
                                title=Title("Custom host"),
                                label=Label("Host name or address"),
                                custom_validate=(LengthInRange(min_value=1),),
                                macro_support=True,
                            ),
                        ),
                    ],
                    prefill=DefaultValue("ip_address"),
                    title=Title("Specify Proxmox VE host via.."),
                ),
            ),
            "no_cert_check": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Disable SSL certificate validation"),
                    label=Label("SSL certificate validation is disabled"),
                )
            ),
            "timeout": DictElement(
                parameter_form=Integer(
                    title=Title("Query Timeout"),
                    help_text=Help("The network timeout in seconds"),
                    prefill=DefaultValue(50),
                    unit_symbol="seconds",
                    custom_validate=(validators.NumberInRange(min_value=1),),
                )
            ),
            "log_cutoff_weeks": DictElement(
                parameter_form=Integer(
                    title=Title("Maximum log age"),
                    help_text=Help("Age in weeks of log data to fetch"),
                    prefill=DefaultValue(2),
                    unit_symbol="weeks",
                )
            ),
        },
        title=Title("Proxmox VE"),
        migrate=_migrate_element_names,
    )


rule_spec_proxmox_ve = SpecialAgent(
    name="proxmox_ve",
    title=Title("Proxmox VE"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=_form_special_agents_proxmox_ve,
)
