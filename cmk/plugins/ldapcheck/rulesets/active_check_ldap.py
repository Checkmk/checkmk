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
    Integer,
    LevelDirection,
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


def _migrate_to_float(value: object) -> float:
    match value:
        case int() | float():
            return float(value)
    raise ValueError(f"Expected int or float, got {type(value)}")


def _migrate_to_dict(value: object) -> dict[str, object]:
    match value:
        case name, password:
            return {"bind_dn": name, "password": password}
        case dict():
            return value
    raise ValueError(f"Expected tuple or dict, got {type(value)}")


def _make_parameter_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This check uses <tt>check_ldap</tt> from the standard "
            "Nagios plug-ins in order to try the response of an LDAP "
            "server."
        ),
        elements={
            "name": DictElement(
                parameter_form=String(
                    title=Title("Name"),
                    help_text=Help(
                        "The service name will be <b>LDAP</b> plus this name. If the name starts with "
                        "a caret (<tt>^</tt>), the service name will not be prefixed with <tt>LDAP</tt>."
                    ),
                    custom_validate=(validators.LengthInRange(1, None),),
                    macro_support=True,
                ),
                required=True,
            ),
            "base_dn": DictElement(
                parameter_form=String(
                    title=Title("Base DN"),
                    help_text=Help("LDAP base, e.g. ou=Development, o=Checkmk GmbH, c=de"),
                    custom_validate=(validators.LengthInRange(1, None),),
                    field_size=FieldSize.LARGE,
                    macro_support=True,
                ),
                required=True,
            ),
            "attribute": DictElement(
                parameter_form=String(
                    title=Title("Attribute to search"),
                    help_text=Help(
                        "LDAP attribute to search, the default is <tt>(objectclass=*)</tt>."
                    ),
                    custom_validate=(validators.LengthInRange(1, None),),
                    prefill=DefaultValue("(objectclass=*)"),
                )
            ),
            "authentication": DictElement(
                parameter_form=Dictionary(
                    title=Title("Authentication"),
                    elements={
                        "bind_dn": DictElement(
                            parameter_form=String(
                                title=Title("Bind DN"),
                                help_text=Help("Distinguished name for binding"),
                                custom_validate=(validators.LengthInRange(1, None),),
                            ),
                            required=True,
                        ),
                        "password": DictElement(
                            parameter_form=Password(
                                title=Title("Password"),
                                help_text=Help(
                                    "Password for binding, if your server requires an authentication"
                                ),
                                migrate=migrate_to_password,
                            ),
                            required=True,
                        ),
                    },
                    migrate=_migrate_to_dict,
                ),
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("TCP Port"),
                    help_text=Help(
                        "Default is 389 for normal connections and 636 for SSL connections."
                    ),
                    custom_validate=(validators.NetworkPort(),),
                    prefill=DefaultValue(389),
                )
            ),
            "ssl": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    label=Label("Use SSL"),
                    title=Title("Use LDAPS (SSL)"),
                    help_text=Help(
                        "Use LDAPS (LDAP SSLv2 method). This sets the default port number to 636"
                    ),
                )
            ),
            "hostname": DictElement(
                parameter_form=String(
                    title=Title("Alternative host name"),
                    help_text=Help(
                        "Use a alternative field as host name in case of SSL Certificate Problems (e.g. the Hostalias )"
                    ),
                    custom_validate=(validators.LengthInRange(1, None),),
                    prefill=DefaultValue("$HOSTALIAS$"),
                    macro_support=True,
                )
            ),
            "version": DictElement(
                parameter_form=SingleChoice(
                    title=Title("LDAP Version"),
                    help_text=Help("The default is to use version 2"),
                    elements=(
                        SingleChoiceElement("v2", Title("Version 2")),
                        SingleChoiceElement("v3", Title("Version 3")),
                        SingleChoiceElement("v3tls", Title("Version 3 and TLS")),
                    ),
                    prefill=DefaultValue("v2"),
                ),
            ),
            "response_time": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Expected response time"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=TimeSpan(
                        displayed_magnitudes=(
                            TimeMagnitude.MILLISECOND,
                            TimeMagnitude.SECOND,
                        ),
                    ),
                    prefill_fixed_levels=DefaultValue((1.0, 2.0)),
                    migrate=lambda v: migrate_to_float_simple_levels(v, 0.001),
                ),
            ),
            "timeout": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Timeout"),
                    help_text=Help("Seconds before connection times out"),
                    displayed_magnitudes=(TimeMagnitude.SECOND,),
                    prefill=DefaultValue(10.0),
                    migrate=_migrate_to_float,
                )
            ),
        },
    )


rule_spec_ldap = ActiveCheck(
    name="ldap",
    title=Title("Check LDAP service access"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_parameter_form,
)
