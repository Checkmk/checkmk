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
    Integer,
    migrate_to_password,
    Password,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NetworkPort, NumberInRange
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _migrate(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise TypeError(value)

    if "no-cert-check" in value:
        value["no_cert_check"] = value.pop("no-cert-check")
    if "no-tls" in value:
        value["no_tls"] = value.pop("no-tls")
    if "basicauth" in value and isinstance(value["basicauth"], tuple):
        username, password = value.pop("basicauth")
        value["basicauth"] = {"username": username, "password": migrate_to_password(password)}
    if "host" in value and value["host"] in ("ip_address", "host_name"):
        value["host"] = (value.pop("host"), None)
    return value


def _parameter_form_special_agents_cisco_prime() -> Dictionary:
    return Dictionary(
        elements={
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
                            parameter_form=Dictionary(
                                elements={
                                    "host": DictElement(
                                        parameter_form=String(
                                            title=Title("Custom host"),
                                            custom_validate=(LengthInRange(min_value=1),),
                                            macro_support=True,
                                        ),
                                        required=True,
                                    ),
                                }
                            ),
                        ),
                    ],
                    prefill=DefaultValue("ip_address"),
                    title=Title("Host to use for connecting to Cisco Prime"),
                ),
            ),
            "basicauth": DictElement(
                parameter_form=Dictionary(
                    title=Title("BasicAuth settings (optional)"),
                    help_text=Help("The credentials for api calls with authentication."),
                    elements={
                        "username": DictElement(
                            parameter_form=String(
                                title=Title("Username"),
                                custom_validate=(LengthInRange(min_value=1),),
                            ),
                            required=True,
                        ),
                        "password": DictElement(
                            parameter_form=Password(
                                title=Title("Password of the user"),
                                custom_validate=(LengthInRange(min_value=1),),
                            ),
                            required=True,
                        ),
                    },
                ),
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("Port"),
                    prefill=DefaultValue(8080),
                    custom_validate=(NetworkPort(),),
                )
            ),
            "no_tls": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Don't use TLS/SSL/Https (unsecure)"),
                    label=Label("TLS/SSL/Https disabled"),
                ),
            ),
            "no_cert_check": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Disable SSL certificate validation"),
                    label=Label("SSL certificate validation is disabled"),
                ),
            ),
            "timeout": DictElement(
                parameter_form=Integer(
                    title=Title("Connect timeout"),
                    help_text=Help("The network timeout in seconds"),
                    prefill=DefaultValue(60),
                    custom_validate=(NumberInRange(min_value=1),),
                    unit_symbol="s",
                ),
            ),
        },
        migrate=_migrate,
    )


rule_spec_cisco_prime = SpecialAgent(
    name="cisco_prime",
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=_parameter_form_special_agents_cisco_prime,
    title=Title("Cisco Prime"),
)
