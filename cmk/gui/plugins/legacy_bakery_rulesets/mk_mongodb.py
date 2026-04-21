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
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate_auth(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Unexpected value: {value!r}")
    if "password" not in value:
        return value
    return {**value, "password": migrate_to_password(value["password"])}


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "deployment" in value:
        return value
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    if value is True:
        return {"deployment": ("sync", None)}
    if isinstance(value, dict):
        return {"deployment": ("sync", None), "auth": value}
    raise ValueError(f"Unexpected value: {value!r}")


def _tls_form() -> Dictionary:
    return Dictionary(
        title=Title("Enable TLS"),
        elements={
            "insecure": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    label=Label("Ignore certificate errors (insecure)"),
                    prefill=DefaultValue(False),
                ),
            ),
            "ca_file": DictElement(
                parameter_form=String(
                    title=Title("Path to CA File"),
                    help_text=Help(
                        "Has to contain a single or a bundle "
                        "of 'certification authority' certificates."
                    ),
                ),
            ),
            "cert_key_file": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Certificate Key File"),
                    help_text=Help(
                        "This is required only if the authentication method is MONGODB-X509"
                    ),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="uploaded_cert_file",
                            title=Title("Upload Certificate key file"),
                            parameter_form=String(
                                title=Title("PEM File content"),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="cert_filepath",
                            title=Title("Path to Certificate key file"),
                            parameter_form=String(
                                title=Title("Path to Cert Key file"),
                                help_text=Help("Has to contain the path to the Cert Key File."),
                            ),
                        ),
                    ),
                ),
            ),
        },
    )


def _auth_form() -> Dictionary:
    return Dictionary(
        title=Title("Authentication"),
        migrate=migrate_auth,
        elements={
            "auth_mechanism": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Authentication mechanism"),
                    elements=(
                        SingleChoiceElement(name="DEFAULT", title=Title("Auto (DEFAULT)")),
                        SingleChoiceElement(
                            name="MONGODB-X509",
                            title=Title("MongoDB >= 5.0 (MONGODB-X509)"),
                        ),
                        SingleChoiceElement(
                            name="SCRAM-SHA-256",
                            title=Title("MongoDB >= 4.0 (SCRAM-SHA-256)"),
                        ),
                        SingleChoiceElement(
                            name="SCRAM-SHA-1",
                            title=Title("MongoDB >= 3.0 (SCRAM-SHA-1)"),
                        ),
                        SingleChoiceElement(
                            name="MONGODB-CR",
                            title=Title("MongoDB < 3.0 (MONGODB-CR)"),
                        ),
                    ),
                    prefill=DefaultValue("DEFAULT"),
                ),
            ),
            "host": DictElement(
                parameter_form=String(
                    title=Title("Host name"),
                    prefill=DefaultValue("localhost"),
                    help_text=Help("The host name of the MongoDB server."),
                ),
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("Port"),
                    prefill=DefaultValue(27017),
                    custom_validate=(validators.NetworkPort(),),
                ),
            ),
            "auth_source": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Authentication source"),
                    prefill=DefaultValue("admin"),
                    help_text=Help("The database to authenticate on."),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "username": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(title=Title("Password")),
            ),
            "tls": DictElement(
                parameter_form=_tls_form(),
            ),
        },
    )


def _valuespec_agent_config_mk_mongodb() -> Dictionary:
    return Dictionary(
        help_text=Help("This will deploy the agent plug-in <tt>mk_mongodb.py</tt>."),
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
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy the mk_mongodb plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
            "auth": DictElement(
                parameter_form=_auth_form(),
            ),
        },
        migrate=migrate,
    )


rule_spec_mk_mongodb = AgentConfig(
    title=Title("MongoDB (Linux)"),
    name="mk_mongodb",
    topic=Topic.DATABASES,
    parameter_form=_valuespec_agent_config_mk_mongodb,
)
