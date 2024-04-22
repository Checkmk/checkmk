#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any

from pydantic import BaseModel

from cmk.utils.config_validation_layer.type_defs import OMITTED_FIELD

TYPE_SITE = str
CONTACT_GROUP_NAME = str
TIME_RANGE = tuple[float, float]


class DisableNotifications(BaseModel):
    disable: bool = OMITTED_FIELD
    timerange: TIME_RANGE = OMITTED_FIELD


class Contact(BaseModel):
    username: str
    alias: str = OMITTED_FIELD
    disable_notifications: DisableNotifications = DisableNotifications()
    email: str = OMITTED_FIELD
    pager: str = OMITTED_FIELD
    contactgroups: list[CONTACT_GROUP_NAME] = OMITTED_FIELD
    fallback_contact: bool = OMITTED_FIELD
    user_scheme_serial: int = OMITTED_FIELD
    authorized_sites: list[TYPE_SITE] = OMITTED_FIELD
    customer: str | None = OMITTED_FIELD


def validate_contacts(contacts: dict[str, Any]) -> None:
    for name, contact in contacts.items():
        validate_contact(name, contact)


def validate_contact(name: str, contact: dict) -> None:
    Contact(username=name, **contact)
