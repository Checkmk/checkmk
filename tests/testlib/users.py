#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import shutil
from pathlib import Path

import cmk.utils.paths

import cmk.gui.config as config
from cmk.gui.utils import get_random_string
from cmk.gui.watolib.users import delete_users, edit_users


def _mk_user_obj(username, password, automation, role):
    # This dramatically improves the performance of the unit tests using this in fixtures
    precomputed_hashes = {
        "Ischbinwischtisch": '$5$rounds=535000$mn3ra3ny1cbHVGsW$5kiJmJcgQ6Iwd1R.i4.kGAQcMF.7zbCt0BOdRG8Mn.9',
    }

    if password not in precomputed_hashes:
        raise ValueError("Add your hash to precomputed_hashes")

    user = {
        username: {
            'attributes': {
                'alias': 'Test user',
                'email': 'test_user_%s@tribe29.com' % username,
                'password': precomputed_hashes[password],
                'notification_method': 'email',
                'roles': [role],
                'serial': 0
            },
            'is_new_user': True,
        }
    }  # type: dict
    if automation:
        user[username]['attributes'].update(automation_secret=password,)
    return user


@contextlib.contextmanager
def create_and_destroy_user(*, automation=False, role="user", username=None):
    if username is None:
        username = u'test123-' + get_random_string(size=5, from_ascii=ord('a'), to_ascii=ord('z'))
    password = u'Ischbinwischtisch'
    edit_users(_mk_user_obj(username, password, automation, role))
    config.load_config()

    profile_path = Path(cmk.utils.paths.omd_root, "var", "check_mk", "web", username)
    profile_path.joinpath('cached_profile.mk').write_text(
        str(
            repr({
                'alias': u'Test user',
                'contactgroups': ['all'],
                'disable_notifications': {},
                'email': u'test_user_%s@tribe29.com' % username,
                'fallback_contact': False,
                'force_authuser': False,
                'locked': False,
                'language': 'de',
                'pager': '',
                'roles': [role],
                'start_url': None,
                'ui_theme': 'modern-dark',
            })))

    yield username, password

    delete_users([username])

    # User directories are not deleted by WATO by default. Clean it up here!
    shutil.rmtree(str(profile_path))
