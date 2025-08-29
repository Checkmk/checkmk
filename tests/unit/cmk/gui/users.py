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

import cmk.utils.paths
from cmk.ccc.user import UserId
from cmk.crypto.password_hashing import PasswordHash
from cmk.gui.config import Config
from cmk.gui.type_defs import UserSpec
from cmk.gui.userdb import get_user_attributes
from cmk.gui.userdb.store import load_users, save_users


def _mk_user_obj(
    username: UserId,
    password: str,
    automation: bool,
    role: str,
    custom_attrs: UserSpec | None = None,
) -> UserSpec:
    # This dramatically improves the performance of the unit tests using this in fixtures
    precomputed_hashes = {
        "Ischbinwischtisch": PasswordHash(
            "$2y$04$E1x6MDiuSlPxeYOfNNkyE.kDQb7SXN5/kqY23eoLyPtZ8eVYzhjsi"
        ),
    }

    if password not in precomputed_hashes:
        raise ValueError("Add your hash to precomputed_hashes")

    user: UserSpec = {
        "alias": "Test user",
        "email": "test_user_%s@checkmk.com" % username,
        "password": precomputed_hashes[password],
        "notification_method": "email",
        "roles": [role],
        "serial": 0,
        "locked": False,
        "contactgroups": ["all"],
    }

    if automation:
        user["store_automation_secret"] = True
        user["automation_secret"] = password

    if custom_attrs is not None:
        user.update(custom_attrs)

    return user


@contextlib.contextmanager
def create_and_destroy_user(
    *,
    automation: bool = False,
    role: str = "user",
    username: str | None = None,
    custom_attrs: UserSpec | None = None,
    config: Config,
) -> Iterator[tuple[UserId, str]]:
    if username is None:
        username = "test123-" + "".join(random.choices(string.ascii_lowercase, k=5))
    password = "Ischbinwischtisch"
    user_id = UserId(username)

    if user_id in config.multisite_users:
        raise ValueError(f"User {user_id} already exists!")

    save_users(
        profiles={
            **load_users(),
            user_id: (
                user := _mk_user_obj(user_id, password, automation, role, custom_attrs=custom_attrs)
            ),
        },
        user_attributes=(user_attributes := get_user_attributes(config.wato_user_attrs)),
        user_connections=config.user_connections,
        now=datetime.now(),
        pprint_value=config.wato_pprint_config,
        call_users_saved_hook=False,
    )

    config.multisite_users[user_id] = user

    try:
        yield user_id, password
    finally:
        config.multisite_users.pop(user_id, None)

        users = load_users()
        if user_id in users:
            del users[user_id]
            save_users(
                profiles=users,
                user_attributes=user_attributes,
                user_connections=config.user_connections,
                now=datetime.now(),
                pprint_value=config.wato_pprint_config,
                call_users_saved_hook=False,
            )

        # User directories are not deleted by WATO by default. Clean it up here!
        shutil.rmtree(str(cmk.utils.paths.omd_root.joinpath("var/check_mk/web", user_id)))
