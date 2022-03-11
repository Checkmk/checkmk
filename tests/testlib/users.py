#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import shutil
from typing import Iterator, Optional

import cmk.utils.paths
from cmk.utils.type_defs import UserId

import cmk.gui.config as config
from cmk.gui.utils import get_random_string
from cmk.gui.utils.logged_in import SuperUserContext
from cmk.gui.watolib.users import delete_users, edit_users


def _mk_user_obj(username: str, password: str, automation: bool, role: str):
    # This dramatically improves the performance of the unit tests using this in fixtures
    precomputed_hashes = {
        "Ischbinwischtisch": "$5$rounds=535000$mn3ra3ny1cbHVGsW$5kiJmJcgQ6Iwd1R.i4.kGAQcMF.7zbCt0BOdRG8Mn.9",
    }

    if password not in precomputed_hashes:
        raise ValueError("Add your hash to precomputed_hashes")

    user = {
        username: {
            "attributes": {
                "alias": "Test user",
                "email": "test_user_%s@tribe29.com" % username,
                "password": precomputed_hashes[password],
                "notification_method": "email",
                "roles": [role],
                "serial": 0,
            },
            "is_new_user": True,
        }
    }  # type: dict
    if automation:
        user[username]["attributes"].update(
            automation_secret=password,
        )
    return user


@contextlib.contextmanager
def create_and_destroy_user(
    *, automation: bool = False, role: str = "user", username: Optional[str] = None
) -> Iterator[tuple[UserId, str]]:
    if username is None:
        username = "test123-" + get_random_string(size=5, from_ascii=ord("a"), to_ascii=ord("z"))
    password = "Ischbinwischtisch"

    # Load the config so that superuser's roles are available
    config.load_config()
    with SuperUserContext():
        edit_users(_mk_user_obj(username, password, automation, role))

    # Load the config with the newly created user
    config.load_config()

    profile_path = cmk.utils.paths.omd_root / "var/check_mk/web" / username
    profile_path.joinpath("cached_profile.mk").write_text(
        str(
            repr(
                {
                    "alias": "Test user",
                    "contactgroups": ["all"],
                    "disable_notifications": {},
                    "email": "test_user_%s@tribe29.com" % username,
                    "fallback_contact": False,
                    "force_authuser": False,
                    "locked": False,
                    "language": "de",
                    "pager": "",
                    "roles": [role],
                    "start_url": None,
                    "ui_theme": "modern-dark",
                }
            )
        )
    )

    yield UserId(username), password

    with SuperUserContext():
        delete_users([username])

    # User directories are not deleted by WATO by default. Clean it up here!
    shutil.rmtree(str(profile_path))
