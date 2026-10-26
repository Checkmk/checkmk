#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
    List,
    migrate_to_password,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate_instance(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Unexpected value: {value!r}")
    match value.get("connection"):
        case ("unix-socket", unix_socket):
            value = {**value, "connection": ("unix_socket", unix_socket)}
        case _other:
            pass
    match value.get("password"):
        case None:
            return {**value, "password": ("no_password", None)}
        case ("no_password", None) | ("password", ("cmk_postprocessed", _, _)):
            return value
        case old_password:
            return {**value, "password": ("password", migrate_to_password(old_password))}


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "deployment" in value:
        return value
    match value:
        case None:
            return {"deployment": ("do_not_deploy", None)}
        case "autodetect":
            return {"deployment": ("sync", None), "instances": ("autodetect", None)}
        case ("static", list() as instances):
            return {
                "deployment": ("sync", None),
                "instances": ("static", [migrate_instance(i) for i in instances]),
            }
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def _instance_form() -> Dictionary:
    return Dictionary(
        migrate=migrate_instance,
        elements={
            "instance": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Name of the instance in the monitoring"),
                    custom_validate=(
                        validators.MatchRegex(
                            "^[A-Za-z0-9_][A-Za-z0-9_-]{0,62}$",
                            Message(
                                "Use at most 63 letters, digits, underscores and "
                                "hyphens, and do not start with a hyphen."
                            ),
                        ),
                    ),
                ),
            ),
            "connection": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Connection"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="tcp",
                            title=Title("TCP"),
                            parameter_form=Dictionary(
                                elements={
                                    "host": DictElement(
                                        required=True,
                                        parameter_form=String(
                                            title=Title("IPv4 address"),
                                            prefill=DefaultValue("127.0.0.1"),
                                            custom_validate=(
                                                validators.LengthInRange(min_value=1),
                                            ),
                                        ),
                                    ),
                                    "port": DictElement(
                                        required=True,
                                        parameter_form=Integer(
                                            title=Title("TCP port number"),
                                            prefill=DefaultValue(6379),
                                            custom_validate=(validators.NetworkPort(),),
                                        ),
                                    ),
                                },
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="unix_socket",
                            title=Title("Unix socket"),
                            parameter_form=Dictionary(
                                elements={
                                    "socket": DictElement(
                                        required=True,
                                        parameter_form=String(
                                            title=Title("Path to Unix socket"),
                                            custom_validate=(
                                                validators.LengthInRange(min_value=1),
                                            ),
                                        ),
                                    ),
                                },
                            ),
                        ),
                    ),
                    prefill=DefaultValue("tcp"),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Password"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="no_password",
                            title=Title("Connect without password"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="password",
                            title=Title("Password"),
                            parameter_form=Password(),
                        ),
                    ),
                    prefill=DefaultValue("no_password"),
                ),
            ),
        },
    )


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "If you activate this option, then the agent plug-in <tt>mk_redis</tt> will be "
            "deployed. You can configure multiple instances or auto-detect running instances."
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
            "instances": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Instances"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="autodetect",
                            title=Title("Auto-detect instances"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="static",
                            title=Title("Specific list of instances"),
                            parameter_form=List(element_template=_instance_form()),
                        ),
                    ),
                    prefill=DefaultValue("autodetect"),
                ),
            ),
        },
    )


rule_spec_mk_redis = AgentConfig(
    title=Title("Redis databases"),
    name="mk_redis",
    topic=Topic.DATABASES,
    parameter_form=_form_spec,
)
