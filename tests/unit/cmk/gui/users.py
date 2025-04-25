#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import random
import shutil
import string
from collections.abc import Iterator
from datetime import datetime

from cmk.ccc.user import UserId

import cmk.utils.paths

from cmk.gui import config
from cmk.gui.session import SuperUserContext
from cmk.gui.type_defs import UserObject, UserSpec
from cmk.gui.userdb.store import load_users, save_users
from cmk.gui.watolib.users import edit_users, user_features_registry

from cmk.crypto.password_hashing import PasswordHash


def _mk_user_obj(
    username: UserId,
    password: str,
    automation: bool,
    role: str,
    custom_attrs: UserSpec | None = None,
) -> UserObject:
    # This dramatically improves the performance of the unit tests using this in fixtures
    precomputed_hashes = {
        "Ischbinwischtisch": PasswordHash(
            "$2y$04$E1x6MDiuSlPxeYOfNNkyE.kDQb7SXN5/kqY23eoLyPtZ8eVYzhjsi"
        ),
    }

    if password not in precomputed_hashes:
        raise ValueError("Add your hash to precomputed_hashes")

    user: UserObject = {
        username: {
            "attributes": {
                "alias": "Test user",
                "email": "test_user_%s@checkmk.com" % username,
                "password": precomputed_hashes[password],
                "notification_method": "email",
                "roles": [role],
                "serial": 0,
                "locked": False,
            },
            "is_new_user": True,
        }
    }

    if automation:
        user[username]["attributes"]["store_automation_secret"] = True
        user[username]["attributes"]["automation_secret"] = password

    if custom_attrs is not None:
        user[username]["attributes"].update(custom_attrs)

    return user


@contextlib.contextmanager
def create_and_destroy_user(
    *,
    automation: bool = False,
    role: str = "user",
    username: str | None = None,
    custom_attrs: UserSpec | None = None,
) -> Iterator[tuple[UserId, str]]:
    if username is None:
        username = "test123-" + "".join(random.choices(string.ascii_lowercase, k=5))
    password = "Ischbinwischtisch"
    user_id = UserId(username)
    del username

    # Load the config so that superuser's roles are available
    config.load_config()
    with SuperUserContext():
        edit_users(
            _mk_user_obj(user_id, password, automation, role, custom_attrs=custom_attrs),
            user_features_registry.features().sites,
        )

    # Load the config with the newly created user
    config.load_config()
    profile_path = cmk.utils.paths.omd_root / "var/check_mk/web" / user_id

    try:
        profile_path.joinpath("cached_profile.mk").write_text(
            str(
                repr(
                    {
                        "alias": "Test user",
                        "contactgroups": ["all"],
                        "disable_notifications": {},
                        "email": "test_user_%s@checkmk.com" % user_id,
                        "fallback_contact": False,
                        "force_authuser": False,
                        "locked": False,
                        "language": "de",
                        "pager": "",
                        "roles": [role],
                        "start_url": None,
                        "ui_theme": "modern-dark",
                        **(custom_attrs or {}),
                    }
                )
            )
        )

        yield user_id, password
    finally:
        with SuperUserContext():
            users = load_users()
            if user_id in users:
                del users[user_id]
                save_users(profiles=users, now=datetime.now())

            # User directories are not deleted by WATO by default. Clean it up here!
            shutil.rmtree(str(profile_path))
