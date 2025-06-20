#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.config import active_config
from cmk.gui.type_defs import UserSpec

# count this up, if new user attributes are used or old are marked as
# incompatible
# 0 -> 1 _remove_flexible_notifications() in 2.2
USER_SCHEME_SERIAL = 1


def new_user_template(connection_id: str) -> UserSpec:
    new_user = UserSpec(
        serial=0,
        connector=connection_id,
        locked=False,
        roles=[],
    )

    # Apply the default user profile
    new_user.update(active_config.default_user_profile)
    return new_user


def add_internal_attributes(usr: UserSpec) -> int:
    usr.setdefault("start_url", "welcome.py")
    return usr.setdefault("user_scheme_serial", USER_SCHEME_SERIAL)
