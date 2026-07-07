#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "url": DictElement(
                required=True,
                parameter_form=String(
                    title=Title(
                        "Base URL of the ExtremeCloud IQ API, e.g. https://api.extremecloudiq.com"
                    ),
                    prefill=DefaultValue("https://api.extremecloudiq.com"),
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
                ),
            ),
        },
    )


rule_spec_special_agent_extremecloud_iq = SpecialAgent(
    name="extremecloud_iq",
    title=Title("Extreme Networks ExtremeCloud IQ"),
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_parameter_form,
)
