#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any

from pydantic import BaseModel, RootModel, ValidationError

from cmk.utils.config_validation_layer.type_defs import Omitted, OMITTED_FIELD
from cmk.utils.config_validation_layer.validation_utils import ConfigValidationError

TYPE_SITE = str
CONTACT_GROUP_NAME = str
TIME_RANGE = tuple[float, float]


class DisableNotifications(BaseModel):
    disable: bool | Omitted = OMITTED_FIELD
    timerange: TIME_RANGE | Omitted = OMITTED_FIELD


class Contact(BaseModel):
    alias: str
    disable_notifications: DisableNotifications = DisableNotifications()
    email: str | Omitted = OMITTED_FIELD
    pager: str | Omitted = OMITTED_FIELD
    contactgroups: list[CONTACT_GROUP_NAME] | Omitted = OMITTED_FIELD
    fallback_contact: bool | Omitted = OMITTED_FIELD
    user_scheme_serial: int | Omitted = OMITTED_FIELD
    authorized_sites: list[TYPE_SITE] | Omitted = OMITTED_FIELD
    customer: str | None | Omitted = OMITTED_FIELD


ContactMapModel = RootModel[dict[str, Contact]]


def validate_contacts(contacts: dict[str, Any]) -> None:
    try:
        ContactMapModel(contacts)

    except ValidationError as exc:
        raise ConfigValidationError(
            which_file="contacts.mk",
            pydantic_error=exc,
            original_data=contacts,
        )
