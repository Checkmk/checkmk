#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    FixedValue,
    migrate_to_password,
    migrate_to_proxy,
    Password,
    Proxy,
    validators,
)

from ._helpers import _get_url_prefix_setting


def form_spec() -> Dictionary:
    return Dictionary(
        title=Title("SIGNL4 Alerting parameters"),
        elements={
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Team Secret"),
                    custom_validate=(
                        validators.LengthInRange(
                            min_value=1,
                            error_msg=Message("Secret access key cannot be empty"),
                        ),
                    ),
                    help_text=Help(
                        "The team secret of your SIGNL4 team. That is the last part of "
                        "your webhook URL: https://connect.signl4.com/webhook/[TEAM_SECRET]"
                    ),
                    migrate=migrate_to_password,
                ),
            ),
            "ignore_ssl": DictElement(
                parameter_form=FixedValue(
                    title=Title("Disable SSL certificate verification"),
                    label=Label("Disable SSL certificate verification"),
                    help_text=Help("Ignore unverified HTTPS request warnings. Use with caution."),
                    value=True,
                )
            ),
            "proxy_url": DictElement(
                parameter_form=Proxy(
                    migrate=migrate_to_proxy,
                )
            ),
            "url_prefix": _get_url_prefix_setting(),
        },
    )
