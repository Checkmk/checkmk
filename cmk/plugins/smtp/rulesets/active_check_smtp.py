#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    InputHint,
    Integer,
    LevelDirection,
    List,
    migrate_to_float_simple_levels,
    migrate_to_password,
    Password,
    SimpleLevels,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic


def _migrate_to_auth(value: object) -> dict[str, object]:
    match value:
        case username, password:
            return {"username": username, "password": password}
        case dict():
            return value
    raise ValueError(f"Invalid value: {value!r}")


def _migrate_to_float(value: object) -> float:
    match value:
        case float() | int():
            return float(value)
    raise ValueError(f"Invalid value: {value!r}")


def _make_parameter_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This check uses <tt>check_smtp</tt> from the standard "
            "Nagios plug-ins in order to try the response of an SMTP "
            "server."
        ),
        elements={
            "name": DictElement(
                parameter_form=String(
                    title=Title("Name"),
                    help_text=Help(
                        "The service name will be <b>SMTP</b> plus this name. If the name starts with "
                        "a caret (<tt>^</tt>), the service name will not be prefixed with <tt>SMTP</tt>."
                    ),
                    custom_validate=(validators.LengthInRange(1, None),),
                    macro_support=True,
                ),
                required=True,
            ),
            "hostname": DictElement(
                parameter_form=String(
                    title=Title("DNS host name or IP address"),
                    custom_validate=(validators.LengthInRange(1, None),),
                    help_text=Help(
                        "You can specify a host name or IP address different from the IP address "
                        "of the host as configured in your host properties."
                    ),
                    macro_support=True,
                ),
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("TCP Port to connect to"),
                    help_text=Help(
                        "The TCP Port the SMTP server is listening on. The default is <tt>25</tt>."
                    ),
                    custom_validate=(validators.NetworkPort(),),
                    prefill=DefaultValue(25),
                )
            ),
            "address_family": DictElement(
                parameter_form=SingleChoice(
                    title=Title("IP address family"),
                    elements=(
                        SingleChoiceElement("primary", Title("Primary address family")),
                        SingleChoiceElement("ipv4", Title("Use any network address")),
                        SingleChoiceElement("ipv6", Title("Enforce IPv6")),
                    ),
                    prefill=DefaultValue("primary"),
                    migrate=lambda x: str(x or "primary"),
                )
            ),
            "expect": DictElement(
                parameter_form=String(
                    title=Title("Expected String"),
                    help_text=Help(
                        "String to expect in first line of server response. "
                        "The default is <tt>220</tt>."
                    ),
                    field_size=FieldSize.SMALL,
                    custom_validate=(validators.LengthInRange(1, None),),
                    prefill=DefaultValue("220"),
                )
            ),
            "commands": DictElement(
                parameter_form=List(
                    element_template=String(),
                    title=Title("SMTP Commands"),
                    help_text=Help("SMTP commands to execute."),
                )
            ),
            "command_responses": DictElement(
                parameter_form=List(
                    element_template=String(),
                    title=Title("SMTP Responses"),
                    help_text=Help("Expected responses to the given SMTP commands."),
                ),
            ),
            "from_address": DictElement(
                parameter_form=String(
                    title=Title("FROM-Address"),
                    help_text=Help(
                        "FROM-address to include in MAIL command, required by Exchange 2000"
                    ),
                    prefill=DefaultValue(""),
                    macro_support=True,
                ),
            ),
            "fqdn": DictElement(
                parameter_form=String(
                    title=Title("FQDN"),
                    help_text=Help("FQDN used for HELO"),
                    prefill=DefaultValue(""),
                    macro_support=True,
                )
            ),
            "cert_days": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Minimum Certificate Age"),
                    help_text=Help("Minimum number of days a certificate has to be valid"),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=(TimeMagnitude.DAY,),
                    ),
                    level_direction=LevelDirection.LOWER,
                    migrate=lambda x: migrate_to_float_simple_levels(x, 86400.0),
                    prefill_fixed_levels=InputHint((864000, 432000)),
                )
            ),
            "starttls": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    label=Label("STARTTLS enabled."),
                    title=Title("Use STARTTLS for the connection."),
                )
            ),
            "auth": DictElement(
                parameter_form=Dictionary(
                    title=Title("Enable SMTP AUTH (LOGIN)"),
                    help_text=Help("SMTP AUTH type to check (default none, only LOGIN supported)"),
                    elements={
                        "username": DictElement(
                            parameter_form=String(
                                title=Title("Username"),
                                field_size=FieldSize.SMALL,
                                custom_validate=(validators.LengthInRange(1, None),),
                            ),
                            required=True,
                        ),
                        "password": DictElement(
                            parameter_form=Password(
                                title=Title("Password"),
                                migrate=migrate_to_password,
                            ),
                            required=True,
                        ),
                    },
                    migrate=_migrate_to_auth,
                ),
            ),
            "response_time": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Expected response time"),
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=(TimeMagnitude.SECOND, TimeMagnitude.MILLISECOND)
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint((1.0, 5.0)),
                    migrate=migrate_to_float_simple_levels,
                )
            ),
            "timeout": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Time before connection times out"),
                    displayed_magnitudes=(TimeMagnitude.SECOND,),
                    prefill=DefaultValue(10.0),
                    migrate=_migrate_to_float,
                )
            ),
        },
    )


rule_spec_smtp = ActiveCheck(
    name="smtp",
    title=Title("Check SMTP service access"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_parameter_form,
)
