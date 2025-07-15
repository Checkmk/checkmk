#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.utils import password_store

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    InputHint,
    migrate_to_proxy,
    Password,
    Proxy,
    SingleChoice,
    SingleChoiceElement,
    String,
)

from ._helpers import _get_url_prefix_setting


def form_spec() -> Dictionary:
    return Dictionary(
        # optional_keys=["ignore_ssl", "proxy_url"],
        title=Title("iLert parameters"),
        elements={
            "ilert_api_key": DictElement(
                parameter_form=Password(
                    title=Title("iLert alert source API key"),
                    help_text=Help("API key for iLert alert server"),
                    migrate=_migrate_to_password,
                ),
                required=True,
            ),
            "ignore_ssl": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Disable SSL certificate verification"),
                    label=Label("Disable SSL certificate verification"),
                    help_text=Help("Ignore unverified HTTPS request warnings. Use with caution."),
                ),
            ),
            "proxy_url": DictElement(
                parameter_form=Proxy(
                    migrate=migrate_to_proxy,
                ),
            ),
            "ilert_priority": DictElement(
                parameter_form=SingleChoice(
                    title=Title(
                        "Notification priority (This will override the "
                        "priority configured in the alert source)"
                    ),
                    prefill=DefaultValue("HIGH"),
                    elements=[
                        SingleChoiceElement(
                            name="HIGH",
                            title=Title("High (with escalation)"),
                        ),
                        SingleChoiceElement(
                            name="LOW",
                            title=Title("Low (without escalation"),
                        ),
                    ],
                )
            ),
            "ilert_summary_host": DictElement(
                parameter_form=String(
                    title=Title("Custom incident summary for host alerts"),
                    prefill=InputHint(
                        "$NOTIFICATIONTYPE$ Host Alert: $HOSTNAME$ is $HOSTSTATE$ - $HOSTOUTPUT$"
                    ),
                    field_size=FieldSize.LARGE,
                )
            ),
            "ilert_summary_service": DictElement(
                parameter_form=String(
                    title=Title("Custom incident summary for service alerts"),
                    prefill=InputHint(
                        "$NOTIFICATIONTYPE$ Service Alert: "
                        "$HOSTALIAS$/$SERVICEDESC$ is $SERVICESTATE$ - "
                        "$SERVICEOUTPUT$"
                    ),
                    field_size=FieldSize.LARGE,
                )
            ),
            "url_prefix": _get_url_prefix_setting(),
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

        if password[0] == "ilert_api_key":
            return (
                "cmk_postprocessed",
                "explicit_password",
                (password_store.ad_hoc_password_id(), password[1]),
            )

        # Already migrated
        assert len(password) == 3
        return password

    raise ValueError(f"Invalid password format: {password}")
