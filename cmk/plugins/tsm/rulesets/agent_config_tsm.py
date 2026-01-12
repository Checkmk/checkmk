#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"


from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    migrate_to_password,
    Password,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _migrate_240_deployment(value: object) -> object:
    match value:
        case ("cached", None):
            return ("sync", None)
        case ("cached", iv):
            return value
        case ("sync", None):
            return value
        case ("sync", iv):
            return ("cached", iv)
        case ("do_not_deploy", _):
            return ("do_not_deploy", None)
        case _:
            raise ValueError(value)


def _migrate_password(value: object) -> object:
    match value:
        case {
            "auth": {"password": ("cmk_postprocesed", "explicit_password", password)} as auth
        } if isinstance(value, dict):
            return {
                **value,
                "auth": {**auth, "password": migrate_to_password(("password", password))},
            }
        case _:
            return value


def _migrate(value: object) -> dict[str, object]:
    if isinstance(value, dict) and "user" in value:
        iv = value.get("interval")
        return {
            "deployment": ("sync", None) if not iv else ("cached", float(iv - iv % 60.0)),
            "auth": {
                "user": value["user"],
                "password": migrate_to_password(("password", value["password"])),
            },
        }

    value = _migrate_password(value)

    match value:
        case None:
            return {"deployment": ("do_not_deploy", None)}
        case {"deployment": deployment} if isinstance(value, dict):
            return {**value, "deployment": _migrate_240_deployment(deployment)}
        case dict():
            return value
        case _:
            raise ValueError(value)


def _agent_config_mk_tsm() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This will deploy the agent plug-in <tt>mk_tsm</tt>. "
            "It will provide several checks concerning TSM."
        ),
        elements={
            "deployment": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy the TSM plug-in and run it synchronously"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="cached",
                            title=Title("Deploy the TSM plug-in and run it asynchronously"),
                            parameter_form=TimeSpan(
                                displayed_magnitudes=(
                                    TimeMagnitude.HOUR,
                                    TimeMagnitude.MINUTE,
                                )
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy the TSM plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
            "auth": DictElement(
                parameter_form=Dictionary(
                    title=Title("Authentication"),
                    elements={
                        "user": DictElement(
                            parameter_form=String(
                                title=Title("Username for login"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                            required=True,
                        ),
                        "password": DictElement(
                            parameter_form=Password(title=Title("Password for login")),
                            required=True,
                        ),
                    },
                ),
            ),
        },
        migrate=_migrate,
    )


rule_spec_tsm_bakelet = AgentConfig(
    name="mk_tsm",
    title=Title("TSM - IBM Tivoli Storage Manager (Linux, Unix)"),
    topic=Topic.STORAGE,
    parameter_form=_agent_config_mk_tsm,
)
