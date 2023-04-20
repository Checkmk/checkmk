#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from datetime import datetime

import pytest
from pytest_mock import MockerFixture

from tests.unit.cmk.gui.test_userdb import _load_users_uncached

from cmk.utils.type_defs import UserId

import cmk.gui.userdb as userdb
from cmk.gui.type_defs import UserSpec

import cmk.update_config.plugins.actions.user_attributes
from cmk.update_config.plugins.actions.user_attributes import UpdateUserAttributes


@pytest.fixture(name="plugin", scope="module")
def fixture_plugin() -> UpdateUserAttributes:
    return UpdateUserAttributes(
        name="user_attributes",
        title="User attributes",
        sort_index=60,
    )


@pytest.mark.parametrize(
    "user, expected",
    [
        pytest.param(
            {
                "alias": "test",
                "email": "",
                "pager": "",
                "contactgroups": [],
                "fallback_contact": False,
                "disable_notifications": {},
                "user_scheme_serial": 0,
                "notifications_enabled": True,
                "notification_period": "24X7",
                "host_notification_options": "durfs",
                "service_notification_options": "wucrfs",
                "notification_method": "email",
                "connector": "htpasswd",
                "locked": False,
                "roles": ["admin"],
                "force_authuser": False,
                "nav_hide_icons_title": None,
                "icons_per_item": None,
                "show_mode": None,
                "enforce_pw_change": False,
                "serial": 0,
                "num_failed_logins": 0,
                "last_pw_change": 1668511745,
            },
            {
                "alias": "test",
                "email": "",
                "pager": "",
                "contactgroups": [],
                "fallback_contact": False,
                "disable_notifications": {},
                "user_scheme_serial": 1,
                "connector": "htpasswd",
                "locked": False,
                "roles": ["admin"],
                "force_authuser": False,
                "nav_hide_icons_title": None,
                "icons_per_item": None,
                "show_mode": None,
                "enforce_pw_change": False,
                "serial": 0,
                "num_failed_logins": 0,
                "last_pw_change": 1668511745,
            },
            id="User with enabled flexible notifications",
        ),
        pytest.param(
            {
                "alias": "test2",
                "email": "",
                "pager": "",
                "contactgroups": [],
                "fallback_contact": False,
                "disable_notifications": {},
                "user_scheme_serial": 0,
                "connector": "htpasswd",
                "locked": False,
                "roles": ["admin"],
                "force_authuser": False,
                "nav_hide_icons_title": None,
                "icons_per_item": None,
                "show_mode": None,
                "enforce_pw_change": False,
                "serial": 0,
                "num_failed_logins": 0,
                "last_pw_change": 1668511745,
            },
            {
                "alias": "test2",
                "email": "",
                "pager": "",
                "contactgroups": [],
                "fallback_contact": False,
                "disable_notifications": {},
                "user_scheme_serial": 1,
                "connector": "htpasswd",
                "locked": False,
                "roles": ["admin"],
                "force_authuser": False,
                "nav_hide_icons_title": None,
                "icons_per_item": None,
                "show_mode": None,
                "enforce_pw_change": False,
                "serial": 0,
                "num_failed_logins": 0,
                "last_pw_change": 1668511745,
            },
            id="User without flexible notifications",
        ),
        pytest.param(
            {
                "alias": "test3",
                "email": "",
                "pager": "",
                "contactgroups": [],
                "fallback_contact": False,
                "disable_notifications": {},
                "user_scheme_serial": 1,
                "connector": "htpasswd",
                "locked": False,
                "roles": ["admin"],
                "force_authuser": False,
                "nav_hide_icons_title": None,
                "icons_per_item": None,
                "show_mode": None,
                "enforce_pw_change": False,
                "serial": 0,
                "num_failed_logins": 0,
                "last_pw_change": 1668511745,
                "temperature_unit": "celsius",
            },
            {
                "alias": "test3",
                "email": "",
                "pager": "",
                "contactgroups": [],
                "fallback_contact": False,
                "disable_notifications": {},
                "user_scheme_serial": 1,
                "connector": "htpasswd",
                "locked": False,
                "roles": ["admin"],
                "force_authuser": False,
                "nav_hide_icons_title": None,
                "icons_per_item": None,
                "show_mode": None,
                "enforce_pw_change": False,
                "serial": 0,
                "num_failed_logins": 0,
                "last_pw_change": 1668511745,
                "temperature_unit": "celsius",
            },
            id="User already updated",
        ),
    ],
)
def test_update_user_attributes(
    user: UserSpec,
    expected: UserSpec,
    plugin: UpdateUserAttributes,
    mocker: MockerFixture,
    with_user: tuple[UserId, str],
) -> None:
    now = datetime.now()
    user_id = with_user[0]
    users: userdb.Users = _load_users_uncached(lock=False)
    users[user_id] = user
    userdb.save_users(users, now)

    mocker.patch.object(
        cmk.update_config.plugins.actions.user_attributes,
        "_flexible_notifications_active",
        return_value=True,
    )
    plugin(logging.getLogger(), {})

    assert _load_users_uncached(lock=False)[user_id] == expected
