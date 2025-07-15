#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime

from cmk.ccc.user import UserId

from cmk.gui.config import active_config
from cmk.gui.type_defs import UserSpec
from cmk.gui.utils import roles, saveint

from .store import load_custom_attr, load_user, save_custom_attr


# userdb.need_to_change_pw returns either None or the reason description why the
# password needs to be changed
def need_to_change_pw(username: UserId, now: datetime) -> str | None:
    # Don't require password change for users from other connections, their passwords are not
    # managed here.
    user = load_user(username)
    if not _is_local_user(user):
        return None

    # Ignore the enforce_pw_change flag for automation users, they cannot change their passwords
    # themselves. (Password age is checked for them below though.)
    if (
        not roles.is_automation_user(username)
        and load_custom_attr(user_id=username, key="enforce_pw_change", parser=saveint) == 1
    ):
        return "enforced"

    last_pw_change = load_custom_attr(user_id=username, key="last_pw_change", parser=saveint)
    max_pw_age = active_config.password_policy.get("max_age")
    if not max_pw_age:
        return None
    if not last_pw_change:
        # The age of the password is unknown. Assume the user has just set
        # the password to have the first access after enabling password aging
        # as starting point for the password period. This bewares all users
        # from needing to set a new password after enabling aging.
        save_custom_attr(username, "last_pw_change", str(int(now.timestamp())))
        return None
    if now.timestamp() - last_pw_change > max_pw_age:
        return "expired"
    return None


def _is_local_user(user: UserSpec) -> bool:
    return user.get("connector", "htpasswd") == "htpasswd"
