#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    List,
    migrate_to_password,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def connection() -> String:
    return String(
        title=Title("URL server address"),
        help_text=Help("Specify a URL to connect to your server. Do not include the protocol."),
        custom_validate=(validators.LengthInRange(min_value=1),),
    )


def api_request_authentication() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Authentication"),
        elements=[
            CascadingSingleChoiceElement(
                name="auth_login",
                title=Title("Basic authentication"),
                parameter_form=Dictionary(
                    elements={
                        "username": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Login username"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                        ),
                        "password": DictElement(
                            required=True,
                            parameter_form=Password(
                                title=Title("Password"),
                                migrate=migrate_to_password,
                            ),
                        ),
                    }
                ),
            ),
            CascadingSingleChoiceElement(
                name="auth_token",
                title=Title("Token authentication"),
                parameter_form=Dictionary(
                    elements={
                        "token": DictElement(
                            required=True,
                            parameter_form=Password(
                                title=Title("Login token"),
                                migrate=migrate_to_password,
                            ),
                        ),
                    },
                ),
            ),
        ],
    )


def _parameter_form() -> Dictionary:
    return Dictionary(
        migrate=_migrate,
        elements={
            "hostname": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Optionally forward output to host"),
                    help_text=Help(
                        "If given forward output to a different host using piggyback mechanics."
                    ),
                ),
            ),
            "connection": DictElement(
                required=True,
                parameter_form=connection(),
            ),
            "verify_cert": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    label=Label("Verify SSL certificate (not verifying is insecure)"),
                    prefill=DefaultValue(False),
                ),
            ),
            "auth_basic": DictElement(
                parameter_form=api_request_authentication(),
            ),
            "protocol": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Protocol"),
                    elements=[
                        SingleChoiceElement("http", Title("HTTP")),
                        SingleChoiceElement("https", Title("HTTPS")),
                    ],
                    prefill=DefaultValue("http"),
                ),
            ),
            "ignore_alerts": DictElement(
                required=True,
                parameter_form=Dictionary(
                    title=Title("Ignore alert rules"),
                    help_text=Help(
                        "The ignore option can target alert rules on different levels including "
                        "specific rules as well as entire rule groups. Matching rules will be filtered "
                        "out on the alertmanager agent side."
                    ),
                    migrate=_migrate_ignore_alerts,
                    elements={
                        "ignore_na": DictElement(
                            required=True,
                            parameter_form=BooleanChoice(
                                label=Label("Ignore alert rules with no status"),
                                help_text=Help(
                                    "Alert rules that don't export a status are ignored with this option."
                                ),
                                prefill=DefaultValue(True),
                            ),
                        ),
                        "ignore_alert_rules": DictElement(
                            required=True,
                            parameter_form=List(
                                title=Title("Ignore specific alert rules"),
                                help_text=Help("Name of specific alert rules you want to ignore."),
                                element_template=String(
                                    custom_validate=(validators.LengthInRange(min_value=1),),
                                ),
                            ),
                        ),
                        "ignore_alert_groups": DictElement(
                            required=True,
                            parameter_form=List(
                                title=Title(
                                    "Ignore all alert rules within certain alert rule groups"
                                ),
                                element_template=String(
                                    custom_validate=(validators.LengthInRange(min_value=1),),
                                ),
                            ),
                        ),
                    },
                ),
            ),
        },
    )


rule_spec_special_agent_alertmanager = SpecialAgent(
    name="alertmanager",
    title=Title("Prometheus Alertmanager"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form,
)


def _migrate(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(value)
    if "verify_cert" in value:
        return value
    migrated_rule = value.copy()
    verify_cert = migrated_rule.pop("verify-cert")
    return migrated_rule | {"verify_cert": verify_cert}


def _migrate_ignore_alerts(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(value)
    return value | ({} if "ignore_na" in value else {"ignore_na": False})
