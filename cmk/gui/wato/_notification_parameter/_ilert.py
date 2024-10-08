#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.form_specs.vue.visitors.recomposers.unknown_form_spec import recompose
from cmk.gui.valuespec import Dictionary as ValueSpecDictionary

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    InputHint,
    Password,
    Proxy,
    SingleChoice,
    SingleChoiceElement,
    String,
)

from ._base import NotificationParameter
from ._helpers import _get_url_prefix_setting


class NotificationParameterILert(NotificationParameter):
    @property
    def ident(self) -> str:
        return "ilert"

    @property
    def spec(self) -> ValueSpecDictionary:
        # TODO needed because of mixed Form Spec and old style setup
        return recompose(self._form_spec()).valuespec  # type: ignore[return-value]  # expects Valuespec[Any]

    def _form_spec(self) -> Dictionary:
        return Dictionary(
            # optional_keys=["ignore_ssl", "proxy_url"],
            title=Title("Create notification with the following parameters"),
            elements={
                "ilert_api_key": DictElement(
                    parameter_form=Password(
                        title=Title("iLert alert source API key"),
                        help_text=Help("API key for iLert alert server"),
                    ),
                    required=True,
                ),
                "ignore_ssl": DictElement(
                    parameter_form=FixedValue(
                        value=True,
                        title=Title("Disable SSL certificate verification"),
                        label=Label("Disable SSL certificate verification"),
                        help_text=Help(
                            "Ignore unverified HTTPS request warnings. Use with caution."
                        ),
                    ),
                ),
                "proxy_url": DictElement(
                    parameter_form=Proxy(),
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
                            "$NOTIFICATIONTYPE$ Host Alert: $HOSTNAME$ is "
                            "$HOSTSTATE$ - $HOSTOUTPUT$"
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
