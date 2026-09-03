#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    List,
    migrate_to_password,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate_auth(value: object) -> tuple[str, object]:
    match value:
        case "system":
            return "system", None
        case ("system", None):
            return "system", None
        case ("db", dict() as credentials) if "user" in credentials:
            return "db", credentials
        case ("db", (str() as user, str() as password)):
            # The old rule set stored the password as a plain string.
            return "db", {"user": user, "password": migrate_to_password(("password", password))}
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def migrate_instance_auth(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "instance" in value:
        return value
    match value:
        case (str() as instance, auth):
            return {"instance": instance, "auth": migrate_auth(auth)}
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def migrate(value: object) -> Mapping[str, object]:
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    if not isinstance(value, dict):
        raise ValueError(f"Unexpected value: {value!r}")
    if "deployment" in value:
        return value
    # Old rule ("first matching rule wins"): make all parameters explicit so that merging with
    # other rules does not change the outcome. 15 and 30 seconds are the defaults of ADO.
    return {
        "deployment": ("sync", None),
        "auth_default": migrate_auth(value.get("auth_default", "system")),
        "auth_instances": [migrate_instance_auth(i) for i in value.get("auth_instances", [])],
        "inst_excludes": value.get("inst_excludes", []),
        "timeout_connection": value.get("timeout_connection", 15),
        "timeout_command": value.get("timeout_command", 30),
    }


def _auth_form(title: Title) -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=title,
        elements=(
            CascadingSingleChoiceElement(
                name="system",
                title=Title("System authentication"),
                parameter_form=FixedValue(value=None),
            ),
            CascadingSingleChoiceElement(
                name="db",
                title=Title("Database user credentials"),
                parameter_form=Dictionary(
                    elements={
                        "user": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("User ID"),
                                prefill=DefaultValue("monitoring"),
                            ),
                        ),
                        "password": DictElement(
                            required=True,
                            parameter_form=Password(title=Title("Password")),
                        ),
                    },
                ),
            ),
        ),
        prefill=DefaultValue("system"),
    )


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This plug-in is deprecated and will be removed in Checkmk 2.4.0 (see Werk "
            '15844 for details). Please switch to the new rule set "Microsoft SQL server '
            '(Linux, Windows)". '
            "This plug-in can be used to collect information of all running MSSQL servers "
            "on the local system. "
            'The current implementation of the check uses the "trusted authentication" '
            "where no user/password needs to be created in the MSSQL server instance by "
            "default. Using this method, you need to grant the user running the Checkmk "
            "Windows agent service access to the MSSQL database. Otherwise you "
            "can configure the credentials of a database user who has the permission to "
            "read the needed information from the server instance."
        ),
        migrate=migrate,
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
                            name="do_not_deploy",
                            title=Title("Do not deploy the plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
            "auth_default": DictElement(
                parameter_form=_auth_form(Title("Authentication (defaults)")),
            ),
            "auth_instances": DictElement(
                parameter_form=List(
                    title=Title("Authentication (instance-specific)"),
                    element_template=Dictionary(
                        migrate=migrate_instance_auth,
                        elements={
                            "instance": DictElement(
                                required=True,
                                parameter_form=String(title=Title("Instance ID")),
                            ),
                            "auth": DictElement(
                                required=True,
                                parameter_form=_auth_form(Title("Authentication")),
                            ),
                        },
                    ),
                ),
            ),
            "inst_excludes": DictElement(
                parameter_form=List(
                    title=Title("Exclude instances"),
                    element_template=String(),
                ),
            ),
            "timeout_connection": DictElement(
                parameter_form=Integer(
                    title=Title("Set connection timeout"),
                    help_text=Help(
                        "Time to wait for a connection to an instance to open "
                        "before continuing with the next instance. If unset, the "
                        "default value from ADO is used."
                    ),
                    unit_symbol="s",
                    prefill=DefaultValue(15),
                    custom_validate=(validators.NumberInRange(min_value=0),),
                ),
            ),
            "timeout_command": DictElement(
                parameter_form=Integer(
                    title=Title("Set command timeout"),
                    help_text=Help(
                        "Time to wait for a command to finish before continuing "
                        "with the next command. If unset, the default value from "
                        "ADO is used."
                    ),
                    unit_symbol="s",
                    prefill=DefaultValue(30),
                    custom_validate=(validators.NumberInRange(min_value=0),),
                ),
            ),
        },
    )


rule_spec_mssql = AgentConfig(
    title=Title("Microsoft SQL Server"),
    name="mssql",
    topic=Topic.DATABASES,
    parameter_form=_form_spec,
    is_deprecated=True,
)
