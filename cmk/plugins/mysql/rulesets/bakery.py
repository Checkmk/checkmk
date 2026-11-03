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
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate_credentials(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "user" in value:
        return value
    match value:
        case (str() as user, password):
            return {"user": user, "password": migrate_to_password(password)}
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
    # other rules does not change the outcome. An empty host means "not configured".
    return {
        "deployment": (
            ("cached", float(value["interval"])) if "interval" in value else ("sync", None)
        ),
        "credentials": (
            ("credentials", migrate_credentials(value["credentials"]))
            if "credentials" in value
            else ("no_credentials", None)
        ),
        "sockets": value.get("sockets", []),
        "host": value.get("host", ""),
        "custom_port": (
            ("custom", value["custom_port"]) if "custom_port" in value else ("default", None)
        ),
    }


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This will deploy the agent plug-in <tt>mk_mysql</tt> on Linux systems and "
            "<tt>mk_mysql.ps1</tt> on Windows systems for monitoring several aspects "
            "of MySQL databases. On Windows, the plug-in will look for service names containing the "
            "strings <tt>MySQL</tt> or <tt>MariaDB</tt>."
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
                            name="cached",
                            title=Title("Deploy the plug-in and run it asynchronously"),
                            parameter_form=TimeSpan(
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                ),
                                prefill=DefaultValue(300.0),
                            ),
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
            "credentials": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Credentials to access the database"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="no_credentials",
                            title=Title("Do not configure credentials"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="credentials",
                            title=Title("Configure credentials"),
                            parameter_form=Dictionary(
                                migrate=migrate_credentials,
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
                    prefill=DefaultValue("no_credentials"),
                ),
            ),
            "sockets": DictElement(
                parameter_form=List(
                    title=Title("Sockets"),
                    help_text=Help(
                        "The default MySQL socket is <tt>/var/run/mysqld/mysqld.sock</tt>."
                    ),
                    element_template=Dictionary(
                        elements={
                            "socket": DictElement(
                                required=True,
                                parameter_form=String(
                                    title=Title("Socket"),
                                    custom_validate=(validators.LengthInRange(min_value=1),),
                                ),
                            ),
                            "alias": DictElement(
                                parameter_form=String(
                                    title=Title("Alias"),
                                    help_text=Help("An optional alias name for your MySQL socket"),
                                ),
                            ),
                        },
                    ),
                ),
            ),
            "host": DictElement(
                parameter_form=String(
                    title=Title("Host"),
                    prefill=DefaultValue("127.0.0.1"),
                ),
            ),
            "custom_port": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Port"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="default",
                            title=Title("Do not configure a port"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="custom",
                            title=Title("Custom port"),
                            parameter_form=Integer(
                                prefill=DefaultValue(3306),
                                custom_validate=(validators.NetworkPort(),),
                            ),
                        ),
                    ),
                    prefill=DefaultValue("default"),
                ),
            ),
        },
    )


rule_spec_mk_mysql = AgentConfig(
    title=Title("MySQL databases"),
    name="mk_mysql",
    topic=Topic.DATABASES,
    parameter_form=_form_spec,
)
