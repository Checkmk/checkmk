#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

from cmk.gui.form_specs.vue.visitors.recomposers.unknown_form_spec import recompose
from cmk.gui.valuespec import Dictionary as ValueSpecDictionary
from cmk.gui.watolib.notification_parameter import NotificationParameter

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    migrate_to_password,
    migrate_to_proxy,
    Password,
    Proxy,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)


class NotificationParameterSMSviaIP(NotificationParameter):
    @property
    def ident(self) -> str:
        return "sms_api"

    @property
    def spec(self) -> ValueSpecDictionary:
        return cast(ValueSpecDictionary, recompose(self._form_spec()).valuespec)

    def _form_spec(self) -> Dictionary:
        return Dictionary(
            title=Title("Create notification with the following parameters"),
            elements={
                "modem_type": DictElement(
                    required=True,
                    parameter_form=SingleChoice(
                        title=Title("Modem type"),
                        help_text=Help(
                            "Choose what modem is used. Currently supported "
                            "is only Teltonika-TRB140."
                        ),
                        elements=[
                            SingleChoiceElement(
                                name="trb140",
                                title=Title("Teltonika-TRB140"),
                            ),
                        ],
                    ),
                ),
                "url": DictElement(
                    required=True,
                    parameter_form=String(
                        title=Title("Modem URL"),
                        help_text=Help(
                            "Choose what modem is used. Currently supported "
                            "is only Teltonika-TRB140."
                        ),
                        custom_validate=[
                            validators.LengthInRange(
                                min_value=1,
                                error_msg=Message("Modem URL cannot be empty"),
                            )
                        ],
                    ),
                ),
                "ignore_ssl": DictElement(
                    parameter_form=FixedValue(
                        title=Title("Disable SSL certificate verification"),
                        label=Label("Disable SSL certificate verification"),
                        help_text=Help(
                            "Ignore unverified HTTPS request warnings. Use with caution."
                        ),
                        value=True,
                    )
                ),
                "proxy_url": DictElement(
                    required=True,
                    parameter_form=Proxy(
                        migrate=migrate_to_proxy,
                    ),
                ),
                "username": DictElement(
                    required=True,
                    parameter_form=String(
                        title=Title("Username"),
                        help_text=Help("The user, used for login."),
                        custom_validate=(
                            validators.LengthInRange(
                                min_value=1,
                                error_msg=Message("Username cannot be empty"),
                            ),
                        ),
                    ),
                ),
                "password": DictElement(
                    required=True,
                    parameter_form=Password(
                        title=Title("Password of the user"),
                        custom_validate=(
                            validators.LengthInRange(
                                min_value=1,
                                error_msg=Message("Password cannot be empty"),
                            ),
                        ),
                        migrate=migrate_to_password,
                    ),
                ),
                "timeout": DictElement(
                    required=True,
                    parameter_form=String(
                        title=Title("Set optional timeout for connections to the modem."),
                        help_text=Help("Here you can configure timeout settings."),
                        prefill=DefaultValue("10"),
                    ),
                ),
            },
        )
