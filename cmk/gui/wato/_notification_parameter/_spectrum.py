#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ipaddress
from typing import cast

from cmk.gui.form_specs.vue.visitors.recomposers.unknown_form_spec import recompose
from cmk.gui.valuespec import Dictionary as ValueSpecDictionary
from cmk.gui.watolib.notification_parameter import NotificationParameter

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    migrate_to_password,
    Password,
    String,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError


class NotificationParameterSpectrum(NotificationParameter):
    @property
    def ident(self) -> str:
        return "spectrum"

    @property
    def spec(self) -> ValueSpecDictionary:
        # TODO needed because of mixed Form Spec and old style setup
        return cast(ValueSpecDictionary, recompose(self._form_spec()).valuespec)

    def _form_spec(self):
        return Dictionary(
            title=Title("Create notification with the following parameters"),
            elements={
                "destination": DictElement(
                    required=True,
                    parameter_form=String(
                        title=Title("Destination IP"),
                        help_text=Help("IP address of the Spectrum server receiving the SNMP trap"),
                        custom_validate=[_validate_ip_address],
                    ),
                ),
                "community": DictElement(
                    required=True,
                    parameter_form=Password(
                        title=Title("SNMP community"),
                        help_text=Help("SNMP community for the SNMP trap"),
                        migrate=migrate_to_password,
                    ),
                ),
                "baseoid": DictElement(
                    required=True,
                    parameter_form=String(
                        title=Title("Base OID"),
                        help_text=Help("The base OID for the trap content"),
                        prefill=DefaultValue("1.3.6.1.4.1.1234"),
                    ),
                ),
            },
        )


def _validate_ip_address(value: str) -> None:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        raise ValidationError(Message("Invalid IP address"))
