#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    FieldSize,
    migrate_to_password,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        help_text=Help("Activate monitoring of the HiveManagerNG cloud."),
        elements={
            "url": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("URL to HiveManagerNG, e.g. https://cloud.aerohive.com"),
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
            "vhm_id": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Numerical ID of the VHM, e.g. 102"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "api_token": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("API access token"),
                    field_size=FieldSize.LARGE,
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "client_id": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Client ID"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "client_secret": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Client secret"),
                    migrate=migrate_to_password,
                ),
            ),
            "redirect_url": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Redirect URL (has to be https)"),
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
        },
    )


rule_spec_special_agent_hivemanager_ng = SpecialAgent(
    name="hivemanager_ng",
    title=Title("Aerohive HiveManager NG"),
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_parameter_form,
)
