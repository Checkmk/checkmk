#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ipaddress
from typing import Literal
from uuid import uuid4

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Password,
    String,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError


def form_spec() -> Dictionary:
    return Dictionary(
        title=Title("Spectrum Server parameters"),
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
                    migrate=_migrate_to_password,
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


def _migrate_to_password(
    model: object,
) -> tuple[
    Literal["cmk_postprocessed"], Literal["explicit_password", "stored_password"], tuple[str, str]
]:
    match model:
        # old password format
        case str(password):
            return (
                "cmk_postprocessed",
                "explicit_password",
                (str(uuid4()), password),
            )
        case "cmk_postprocessed", "explicit_password", (str(password_id), str(password)):
            return "cmk_postprocessed", "explicit_password", (password_id, password)
        case "cmk_postprocessed", "stored_password", (str(password_store_id), str(password)):
            return "cmk_postprocessed", "stored_password", (password_store_id, password)

    raise TypeError(f"Could not migrate {model!r} to Password.")
