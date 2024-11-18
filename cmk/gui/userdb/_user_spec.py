#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pydantic import TypeAdapter

from cmk.gui.config import active_config
from cmk.gui.type_defs import UserContactDetails, UserDetails, UserSpec

# count this up, if new user attributes are used or old are marked as
# incompatible
# 0 -> 1 _remove_flexible_notifications() in 2.2
USER_SCHEME_SERIAL = 1


def new_user_template(connection_id: str) -> UserSpec:
    new_user = UserSpec(
        serial=0,
        connector=connection_id,
        locked=False,
    )

    # Apply the default user profile
    new_user.update(active_config.default_user_profile)
    return new_user


def add_internal_attributes(usr: UserSpec) -> int:
    return usr.setdefault("user_scheme_serial", USER_SCHEME_SERIAL)


def validate_users_details(users: object) -> dict[str, UserDetails]:
    # Performance impact needs to be investigated (see CMK-19527)
    # nosemgrep: type-adapter-detected
    validator = TypeAdapter(dict[str, UserDetails])
    return validator.validate_python(users, strict=True)


def validate_contact_details(contacts: object) -> dict[str, UserContactDetails]:
    # Performance impact needs to be investigated (see CMK-19527)
    # nosemgrep: type-adapter-detected
    validator = TypeAdapter(dict[str, UserContactDetails])
    return validator.validate_python(contacts, strict=True)
