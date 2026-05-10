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
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        return {"deployment": ("do_not_deploy", None)}
    if "deployment" in value:
        return value
    return {
        "deployment": ("sync", None),
        **value,
    }


def migrate_instance(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        return value  # type: ignore[return-value]
    if "instance_name" not in value:
        return {**value, "instance_name": ""}
    return value


def _instance_settings() -> Dictionary:
    return Dictionary(
        migrate=migrate_instance,
        elements={
            "instance_env_filepath": DictElement(
                required=True,
                parameter_form=String(
                    title=Title(
                        "The environment file of the PostgreSQL instance. This file"
                        ' contains variables of the form `PGPORT="5432"`. Check the'
                        " header of the agent plug-in for a more detailed description."
                    ),
                ),
            ),
            "instance_name": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Instance name"),
                    help_text=Help(
                        "The name of the instance to be monitored. If left empty, the"
                        " instance name is determined based on the name of the environment"
                        " file. For example, if you have specified the name"
                        " `/home/postgres/db.env`, then the plug-in will remove the"
                        " directory and the trailing `.env`. This results in the instance"
                        " name `db`. Using this mechanism is not recommended. It is kept"
                        " around for backwards compability."
                    ),
                ),
            ),
            "instance_username": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Instance username"),
                ),
            ),
            "instance_pgpass_filepath": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Path to .pgpass file"),
                ),
            ),
        },
    )


def _instances_settings() -> Dictionary:
    return Dictionary(
        title=Title("Instances settings"),
        elements={
            "db_username": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("DB username"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "pg_binary_path": DictElement(
                parameter_form=String(
                    title=Title("Path to PostgreSQL binary"),
                    help_text=Help(
                        "By default, the agent determines the location dynamically"
                        " based on a few well-known locations. You can specify a"
                        " full path here instead."
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "instances": DictElement(
                required=True,
                parameter_form=List(
                    title=Title("Monitor multiple instances on the host"),
                    add_element_label=Label("Add instance to be monitored"),
                    element_template=_instance_settings(),
                ),
            ),
        },
    )


def _valuespec_agent_config_mk_postgres() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Deploy the agent plug-in <tt>mk_postgres</tt>. This will create"
            " information necessary for all <tt>postgres_*</tt> checks."
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
                                )
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
            "instances_settings": DictElement(
                parameter_form=_instances_settings(),
            ),
        },
        migrate=migrate,
    )


rule_spec_mk_postgres = AgentConfig(
    title=Title("PostgreSQL database and sessions (Linux, Windows)"),
    name="mk_postgres",
    topic=Topic.DATABASES,
    parameter_form=_valuespec_agent_config_mk_postgres,
)
