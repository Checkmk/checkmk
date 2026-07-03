#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    migrate_to_password,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _migrate(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(value)

    if "username" in value:
        # Already in the ExtremeCloud IQ shape.
        return value

    # Legacy Aerohive rules carried "vhm_id", "api_token", "client_id",
    # "client_secret" and "redirect_url". The ExtremeCloud IQ API authenticates
    # with username and password instead, so only the URL can be carried over;
    # the credentials have to be entered again.
    return {"url": value["url"]}


def _parameter_form() -> Dictionary:
    return Dictionary(
        help_text=Help("Activate monitoring of the ExtremeCloud IQ (HiveManager NG) cloud."),
        migrate=_migrate,
        elements={
            "url": DictElement(
                required=True,
                parameter_form=String(
                    title=Title(
                        "Base URL of the ExtremeCloud IQ API, e.g. https://api.extremecloudiq.com"
                    ),
                    custom_validate=(
                        validators.Url(
                            protocols=[
                                validators.UrlProtocol.HTTP,
                                validators.UrlProtocol.HTTPS,
                            ]
                        ),
                    ),
                ),
            ),
            "username": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("ExtremeCloud IQ username"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("ExtremeCloud IQ password"),
                    migrate=migrate_to_password,
                ),
            ),
        },
    )


rule_spec_special_agent_hivemanager_ng = SpecialAgent(
    name="hivemanager_ng",
    title=Title("Aerohive HiveManager NG / ExtremeCloud IQ"),
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_parameter_form,
)
