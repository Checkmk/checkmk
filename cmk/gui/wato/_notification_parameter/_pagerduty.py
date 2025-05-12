#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.utils import password_store

from cmk.gui.form_specs.private.dictionary_extended import DictionaryExtended
from cmk.gui.http import request

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    FixedValue,
    migrate_to_proxy,
    Password,
    Proxy,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange

from ._helpers import _get_url_prefix_setting


def form_spec() -> DictionaryExtended:
    # TODO register CSE specific version
    return DictionaryExtended(
        title=Title("PagerDuty parameters"),
        elements={
            "routing_key": DictElement(
                parameter_form=Password(
                    title=Title("PagerDuty Service Integration Key"),
                    migrate=_migrate_to_password,
                    custom_validate=[
                        LengthInRange(
                            min_value=1,
                            error_msg=Message("Please enter a Service Integration Key"),
                        ),
                    ],
                ),
                required=True,
            ),
            "webhook_url": DictElement(
                parameter_form=FixedValue(
                    title=Title("API endpoint from PagerDuty V2"),
                    value="https://events.pagerduty.com/v2/enqueue",
                ),
                required=True,
            ),
            "ignore_ssl": DictElement(
                parameter_form=FixedValue(
                    title=Title("Disable SSL certificate verification"),
                    label=Label("Disable SSL certificate verification"),
                    value="https://events.pagerduty.com/v2/enqueue",
                    help_text=Help("Ignore unverified HTTPS request warnings. Use with caution."),
                )
            ),
            "proxy_url": DictElement(
                parameter_form=Proxy(
                    migrate=migrate_to_proxy,
                ),
            ),
            "url_prefix": _get_url_prefix_setting(
                default_value="automatic_https" if request.is_ssl_request else "automatic_http",
            ),
        },
    )


def _migrate_to_password(
    password: object,
) -> tuple[
    Literal["cmk_postprocessed"],
    Literal["explicit_password", "stored_password"],
    tuple[str, str],
]:
    if isinstance(password, tuple):
        if password[0] == "store":
            return ("cmk_postprocessed", "stored_password", (password[1], ""))

        if password[0] == "routing_key":
            return (
                "cmk_postprocessed",
                "explicit_password",
                (password_store.ad_hoc_password_id(), password[1]),
            )

        # Already migrated
        assert len(password) == 3
        return password

    raise ValueError(f"Invalid password format: {password}")
