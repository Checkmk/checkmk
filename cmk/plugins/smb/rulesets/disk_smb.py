#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ipaddress
from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    LevelDirection,
    LevelsType,
    migrate_to_float_simple_levels,
    migrate_to_password,
    Password,
    Percentage,
    SimpleLevels,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic


def _validate_ip_address(value: str) -> None:
    if value.startswith("$") and value.endswith("$"):
        return
    try:
        ipaddress.ip_address(value)
    except ValueError:
        raise validators.ValidationError(Message("Neither a valid IP address nor a macro"))


def _migrate_host(param: object) -> tuple[str, str]:
    match param:
        case "use_parent_host":
            return ("use_parent_host", "")
        case "define_host", str(host):
            return ("define_host", host)
        case (str(_key), str(_host)):
            return (_key, _host)
    raise ValueError(param)


def _migrate_auth_tuple(params: object) -> Mapping[str, object]:
    match params:
        case (user, password):
            return {"user": user, "password": password}
        case {"user": user, "password": password}:
            return {"user": user, "password": password}
    raise ValueError(params)


def _valuespec_active_checks_disk_smb() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This ruleset helps you to configure the active check "
            "plugin <tt>check_disk_smb</tt> that checks the access to "
            "filesystem shares that are exported via SMB/CIFS."
        ),
        elements={
            "share": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("SMB share to check"),
                    help_text=Help(
                        "Enter the plain name of the share only, e. g. <tt>iso</tt>, <b>not</b> "
                        "the full UNC like <tt>\\\\servername\\iso</tt>"
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "workgroup": DictElement(
                parameter_form=String(
                    title=Title("Workgroup"),
                    help_text=Help("Workgroup or domain used (defaults to <tt>WORKGROUP</tt>)"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "host": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("NetBIOS name of the server"),
                    help_text=Help(
                        "Choose, whether you want to use the parent host information for the NetBIOS server name,"
                        " or if you want to specify one."
                    ),
                    migrate=_migrate_host,
                    elements=[
                        CascadingSingleChoiceElement(
                            name="use_parent_host",
                            title=Title("Use parent host information for the NetBIOS server name"),
                            parameter_form=FixedValue(value=""),
                        ),
                        CascadingSingleChoiceElement(
                            name="define_host",
                            title=Title("Define name of NetBIOS server"),
                            parameter_form=String(
                                custom_validate=(validators.LengthInRange(min_value=1),),
                                help_text=Help("You can specify the NetBIOS server name."),
                            ),
                        ),
                    ],
                ),
            ),
            "ip_address": DictElement(
                parameter_form=String(
                    title=Title("IP address"),
                    help_text=Help(
                        "IP address of SMB share host (only necessary if SMB share host is in another network)"
                    ),
                    custom_validate=(_validate_ip_address,),
                    macro_support=True,
                ),
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("TCP port"),
                    help_text=Help("TCP port number to connect to. Usually either 139 or 445."),
                    prefill=DefaultValue(445),
                    custom_validate=(validators.NetworkPort(),),
                ),
            ),
            "levels": DictElement(
                required=True,
                parameter_form=SimpleLevels(
                    title=Title("Levels for used disk space"),
                    level_direction=LevelDirection.UPPER,
                    migrate=migrate_to_float_simple_levels,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue((85.0, 95.0)),
                    prefill_levels_type=DefaultValue(LevelsType.FIXED),
                ),
            ),
            "auth": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Authorization"),
                    migrate=_migrate_auth_tuple,
                    elements={
                        "user": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Username"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                        ),
                        "password": DictElement(
                            required=True,
                            parameter_form=Password(
                                help_text=Help(
                                    "For security reasons it is recommended to use the password store for setting the password."
                                ),
                                title=Title("Password"),
                                migrate=migrate_to_password,
                            ),
                        ),
                    },
                ),
            ),
        },
    )


rule_spec_active_check_disk_smb = ActiveCheck(
    name="disk_smb",
    title=Title("Check SMB share access"),
    topic=Topic.STORAGE,
    parameter_form=_valuespec_active_checks_disk_smb,
)
