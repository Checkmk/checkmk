#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

import datetime
import random
import string
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import time_machine
from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from cmk.ccc import version
from cmk.ccc.user import UserId
from cmk.crypto.password import PasswordPolicy
from cmk.crypto.password_hashing import PasswordHash
from cmk.gui import userdb
from cmk.gui.config import active_config
from cmk.gui.logged_in import LoggedInSuperUser, user
from cmk.gui.openapi.endpoints.user_config import (
    _api_to_internal_format,
    _internal_to_api_format,
    _load_user,
)
from cmk.gui.openapi.endpoints.utils import complement_customer
from cmk.gui.type_defs import CustomUserAttrSpec, Users, UserSpec
from cmk.gui.userdb import ConnectorType, get_user_attributes, UserRole
from cmk.gui.watolib.custom_attributes import save_custom_attrs_to_mk_file, update_user_custom_attrs
from cmk.gui.watolib.userroles import clone_role, RoleID
from cmk.gui.watolib.users import create_user, default_sites, edit_users
from cmk.utils import paths
from tests.testlib.unit.rest_api_client import ClientRegistry
from tests.unit.cmk.web_test_app import SetConfig

managedtest = pytest.mark.skipif(
    version.edition(paths.omd_root) is not version.Edition.ULTIMATEMT, reason="see #7213"
)

MOCK_SAML_CONNECTOR_NAME = "saml_connector"


@managedtest
def test_nonexistant_customer(clients: ClientRegistry) -> None:
    username = "user"
    customer = "i_do_not_exist"

    clients.User.create(
        username=username, fullname="User Name", customer=customer, expect_ok=False
    ).assert_status_code(400)

    clients.User.create(username=username, fullname="User Name", customer="global")

    clients.User.edit(username=username, customer=customer, expect_ok=False).assert_status_code(400)


@managedtest
def test_idle_timeout(clients: ClientRegistry) -> None:
    username = "user"

    with time_machine.travel(datetime.datetime.fromisoformat("2010-02-01 08:00:00Z")):
        resp = clients.User.create(
            username=username,
            fullname="User Name",
            customer="global",
            idle_timeout={"option": "individual", "duration": 666},
        )

    assert resp.json["extensions"]["idle_timeout"]["duration"] == 666

    resp = clients.User.edit(
        username=username,
        idle_timeout={"option": "individual", "duration": 999},
    )
    assert resp.json["extensions"]["idle_timeout"]["duration"] == 999

    resp = clients.User.edit(
        username=username,
        idle_timeout={"option": "disable"},
    )
    assert resp.json["extensions"]["idle_timeout"]["option"] == "disable"


@managedtest
def test_openapi_customer(clients: ClientRegistry, monkeypatch: MonkeyPatch) -> None:
    username = "user"

    with time_machine.travel(datetime.datetime.fromisoformat("2010-02-01 08:00:00Z")):
        resp = clients.User.create(
            username=username,
            fullname="User Name",
            customer="global",
        )

    assert resp.json["extensions"] == {
        "fullname": "User Name",
        "customer": "global",
        "contactgroups": [],
        "disable_notifications": {},
        "contact_options": {"email": "", "fallback_contact": False},
        "idle_timeout": {"option": "global"},
        "disable_login": False,
        "pager_address": "",
        "roles": [],
        # TODO: auth_option being an empty dict is a bug and should not
        # happen: there should not be a user without connection type (this is
        # what it's called in the GUI) see CMK-12723
        "auth_option": {},
        "interface_options": {
            "interface_theme": "default",
            "main_menu_icons": "topic",
            "mega_menu_icons": "topic",  # TODO: DEPRECATED(18295) remove "mega_menu_icons"
            "navigation_bar_icons": "hide",
            "show_mode": "default",
            "sidebar_position": "right",
            "contextual_help_icon": "show_icon",
        },
        "start_url": "default_start_url",
    }

    resp = clients.User.edit(username=username, customer="provider")

    assert resp.json["extensions"]["customer"] == "provider"


@managedtest
def test_openapi_user_minimal_settings(
    monkeypatch: MonkeyPatch,
    request_context: None,
) -> None:
    with (
        time_machine.travel(datetime.datetime.fromisoformat("2021-09-24 12:36:00Z")),
    ):
        user_object: UserSpec = {
            "ui_theme": None,
            "ui_sidebar_position": None,
            "nav_hide_icons_title": None,
            "icons_per_item": None,
            "show_mode": None,
            "start_url": None,
            "force_authuser": False,
            "enforce_pw_change": False,
            "alias": "User Name",
            "locked": False,
            "pager": "",
            "roles": [],
            "contactgroups": [],
            "email": "",
            "fallback_contact": False,
            "disable_notifications": {},
        }
        create_user(
            UserId("user"),
            user_object,
            default_sites,
            get_user_attributes([]),
            use_git=False,
            acting_user=LoggedInSuperUser(),
        )

    user_attributes = _load_internal_attributes(UserId("user"))
    user_attributes.pop("last_pw_change", None)

    assert user_attributes == {
        "alias": "User Name",
        "customer": "provider",
        "contactgroups": [],
        "disable_notifications": {},
        "email": "",
        "enforce_pw_change": False,
        "fallback_contact": False,
        "locked": False,
        "pager": "",
        "roles": [],
        "user_scheme_serial": 1,
        "num_failed_logins": 0,
        "serial": 0,
        "is_automation_user": False,
        "store_automation_secret": False,
    }


@managedtest
def test_openapi_user_minimal_password_settings(
    clients: ClientRegistry,
    monkeypatch: MonkeyPatch,
) -> None:
    username = "user"

    with time_machine.travel(datetime.datetime.fromisoformat("2010-02-01 08:00:00Z")):
        resp = clients.User.create(
            username=username,
            fullname="User Name",
            customer="provider",
            auth_option={
                "auth_type": "password",
                "password": "password1234",
                "enforce_password_change": True,
            },
        )

    extensions = resp.json["extensions"]
    assert extensions["customer"] == "provider"
    assert extensions["auth_option"]["enforce_password_change"] is True
    assert "last_pw_change" not in extensions
    assert "password" not in extensions

    user_from_db = userdb.load_user(UserId(resp.json["id"]))
    assert user_from_db["connector"]
    assert user_from_db["connector"] == "htpasswd"

    with time_machine.travel(datetime.datetime.fromisoformat("2010-02-01 08:30:00Z")):
        resp = clients.User.edit(
            username=username,
            auth_option={
                "auth_type": "automation",
                "secret": "SOMEAUTOMATION",
            },
            roles=["user"],
            idle_timeout={"option": "disable"},
        )

    extensions = resp.json["extensions"]
    assert extensions["auth_option"] == {
        "auth_type": "automation",
        "store_automation_secret": False,
    }
    assert extensions["idle_timeout"]["option"] == "disable"
    assert extensions["roles"] == ["user"]

    user_from_db = userdb.load_user(UserId(resp.json["id"]))
    assert user_from_db["connector"]
    assert user_from_db["connector"] == "htpasswd"


def test_openapi_all_users(clients: ClientRegistry) -> None:
    resp = clients.User.get_all()
    users = resp.json["value"]
    assert len(users) == 1

    user = clients.User.get(url=users[0]["links"][0]["href"])
    assert user.json == users[0]


@managedtest
def test_openapi_user_config(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    monkeypatch: MonkeyPatch,
) -> None:
    name = _random_string(10)
    alias = "KPECYCq79E"

    with time_machine.travel(datetime.datetime.fromisoformat("2010-02-01 08:30:00Z")):
        clients.User.create(
            username=name,
            fullname=alias,
            customer="provider",
            disable_notifications={
                "timerange": {
                    "start_time": "2020-01-01T00:00:00Z",
                    "end_time": "2020-01-02T00:00:00Z",
                }
            },
        )

    resp = clients.User.get(username=name)

    extensions = resp.json["extensions"]
    assert extensions["disable_notifications"] == {
        "timerange": {
            "end_time": "2020-01-02T00:00:00+00:00",
            "start_time": "2020-01-01T00:00:00+00:00",
        }
    }

    collection_resp = clients.User.get_all()
    assert len(collection_resp.json["value"]) == 2

    clients.User.delete(username=name)
    clients.User.get(username=name, expect_ok=False).assert_status_code(404)

    collection_resp = clients.User.get_all()
    assert len(collection_resp.json["value"]) == 1


@managedtest
def test_openapi_user_internal_with_notifications(
    monkeypatch: MonkeyPatch,
    request_context: None,
) -> None:
    name = UserId(_random_string(10))

    user_object: UserSpec = {
        "ui_theme": None,
        "ui_sidebar_position": None,
        "nav_hide_icons_title": None,
        "icons_per_item": None,
        "show_mode": None,
        "start_url": None,
        "force_authuser": False,
        "enforce_pw_change": True,
        "alias": "KPECYCq79E",
        "locked": False,
        "pager": "",
        "roles": [],
        "contactgroups": [],
        "email": "",
        "fallback_contact": False,
        "password": PasswordHash(
            "$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C"
        ),
        "last_pw_change": 1265013000,
        "serial": 1,
        "disable_notifications": {"timerange": (1577836800.0, 1577923200.0)},
    }
    create_user(
        name,
        user_object,
        default_sites,
        get_user_attributes([]),
        use_git=False,
        acting_user=LoggedInSuperUser(),
    )

    assert _load_internal_attributes(name) == {
        "alias": "KPECYCq79E",
        "customer": "provider",
        "pager": "",
        "contactgroups": [],
        "email": "",
        "fallback_contact": False,
        "disable_notifications": {"timerange": (1577836800.0, 1577923200.0)},
        "user_scheme_serial": 1,
        "locked": False,
        "roles": [],
        "password": "$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C",
        "serial": 1,
        "last_pw_change": 1265013000,
        "enforce_pw_change": True,
        "num_failed_logins": 0,
        "is_automation_user": False,
        "store_automation_secret": False,
    }


test_data_update_auth_options = (
    ({"auth_option": {"auth_type": "password", "password": "newpassword1"}}, 1),
    ({"auth_option": {"auth_type": "automation", "secret": "DEYQEQQPYCFFBYH@AVMC"}}, 1),
    ({"auth_option": {"auth_type": "remove"}}, 1),
    (None, 0),
)


@managedtest
@pytest.mark.parametrize("test_data, expected_serial_count", test_data_update_auth_options)
def test_update_user_auth_options(
    clients: ClientRegistry,
    monkeypatch: MonkeyPatch,
    base: str,
    test_data: Mapping[str, str],
    expected_serial_count: int,
) -> None:
    name = _random_string(10)
    resp = clients.User.create(username=name, fullname="KPECYCq79E", customer="provider")

    user_data = resp.json["extensions"]
    user_data.pop("auth_option", None)

    # TODO: DEPRECATED(18295) remove "mega_menu_icons"
    # Hint Response != Request >> all responses contain alias AND field.
    user_data["interface_options"].pop("mega_menu_icons", None)

    if test_data is not None:
        user_data.update(test_data)

    resp = clients.User.edit(**user_data, username=name)

    serial_count_after = _load_user(UserId(name))["serial"]
    assert serial_count_after == expected_serial_count


@managedtest
def test_openapi_user_edit_auth(clients: ClientRegistry, monkeypatch: MonkeyPatch) -> None:
    name = "foo"
    alias = "Foo Bar"

    with time_machine.travel(datetime.datetime.fromisoformat("2010-02-01 08:00:00Z")):
        resp = clients.User.create(
            username=name,
            fullname=alias,
            customer="provider",
            roles=["user"],
            auth_option={"auth_type": "password", "password": "password1234"},
        )

    extensions = resp.json["extensions"]
    assert extensions["customer"] == "provider"
    assert extensions["auth_option"]["enforce_password_change"] is False

    with time_machine.travel(datetime.datetime.fromisoformat("2010-02-01 08:30:00Z")):
        resp = clients.User.edit(
            username=name, auth_option={"auth_type": "automation", "secret": "QWXWBFUCSUOXNCPJUMS@"}
        )

    with time_machine.travel(datetime.datetime.fromisoformat("2010-02-01 09:00:00Z")):
        resp = clients.User.edit(
            username=name,
            auth_option={
                "auth_type": "remove",
            },
        )


@pytest.fixture(name="with_password_policy")
def fixture_password_policy(set_config: SetConfig) -> Iterator[None]:
    with set_config(password_policy={"min_length": 20}):
        assert active_config.password_policy.get("min_length") == 20
        yield


@pytest.mark.parametrize(
    "password,reason",
    [
        # Fail due to policy (fixture expects 20 chars).
        ("short", "too short"),
        # Fail because the AUTH_PASSWORD schema requires minLength=1. (It also doesn't comply with
        # the policy but we never get to checking that.)
        ("", "These fields have problems: auth_option"),
        # Fail when trying to instantiate the Password object (null bytes not allowed).
        ("\0" * 21, "Password must not contain null bytes"),
    ],
)
def test_openapi_create_user_password_failures(
    clients: ClientRegistry, with_password_policy: None, password: str, reason: str
) -> None:
    """Test that invalid passwords are denied and handled gracefully"""

    user_detail = complement_customer(
        {
            "username": "shortpw",
            "fullname": "Short Password",
            "roles": ["user"],
            "auth_option": {"auth_type": "password", "password": password},
        }
    )

    response = clients.User.create(**user_detail, expect_ok=False).assert_status_code(400)

    assert reason in response.json["detail"]


def test_openapi_automation_enforce_pw_change(clients: ClientRegistry) -> None:
    """
    Test that password change cannot be force for automation users.
    This should be caught by the schema.
    """

    user_detail = complement_customer(
        {
            "username": "automation_enforce_pw_change",
            "fullname": "But I can't!",
            "roles": ["user"],
            "auth_option": {"auth_type": "automation", "enforce_password_change": True},
        }
    )

    response = clients.User.create(**user_detail, expect_ok=False)

    assert "Unknown field." in response.json["fields"]["auth_option"]["enforce_password_change"]


@pytest.mark.parametrize("auth_type", ["password", "automation"])
def test_openapi_incomplete_auth_options(clients: ClientRegistry, auth_type: str) -> None:
    """Test that new users cannot be created without a password / secret"""

    user_detail = complement_customer(
        {
            "username": f"incomplete_auth_options_{auth_type}",
            "fullname": "a new user",
            "roles": ["user"],
            "auth_option": {"auth_type": auth_type},
        }
    )

    clients.User.create(**user_detail, expect_ok=False).assert_status_code(400)


@managedtest
def test_openapi_user_internal_auth_handling(
    monkeypatch: MonkeyPatch,
    request_context: None,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.userdb.htpasswd.hash_password",
        lambda x: "$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C",
    )

    name = UserId("foo")
    password_hash = PasswordHash(
        "$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C"
    )
    user_object: UserSpec = {
        "ui_theme": None,
        "ui_sidebar_position": None,
        "nav_hide_icons_title": None,
        "icons_per_item": None,
        "show_mode": None,
        "start_url": None,
        "force_authuser": False,
        "enforce_pw_change": True,
        "alias": "Foo Bar",
        "locked": False,
        "pager": "",
        "roles": ["user"],
        "contactgroups": [],
        "email": "",
        "fallback_contact": False,
        "password": password_hash,
        "last_pw_change": 1265011200,  # 2010-02-01 08:00:00
        "serial": 1,
        "disable_notifications": {},
    }

    with time_machine.travel(datetime.datetime.fromisoformat("2010-02-01 08:30:00Z")):
        create_user(
            name,
            user_object,
            default_sites,
            get_user_attributes([]),
            use_git=False,
            acting_user=LoggedInSuperUser(),
        )

    loaded = _load_internal_attributes(name)
    assert loaded["password"] == password_hash
    assert loaded["enforce_pw_change"] is True  # from creation
    # last_pw_change should be unchanged, since it uses creation data, not current time
    assert loaded["last_pw_change"] == 1265011200  # 08:00:00
    # defaults for automation user fields
    assert loaded["is_automation_user"] is False
    assert loaded["store_automation_secret"] is False

    with time_machine.travel(datetime.datetime.fromisoformat("2010-02-01 09:00:00Z")):
        updated_internal_attributes = _api_to_internal_format(
            _load_user(name),
            {"auth_option": {"secret": "QWXWBFUCSUOXNCPJUMS@", "auth_type": "automation"}},
            PasswordPolicy(12, None),
        )
        edit_users(
            {name: updated_internal_attributes},
            default_sites,
            get_user_attributes([]),
            use_git=False,
            acting_user=LoggedInSuperUser(),
        )

    loaded = _load_internal_attributes(name)
    assert loaded["last_pw_change"] == 1265014800  # 09:00:00 -- changed as secret was changed
    assert loaded["is_automation_user"] is True
    assert loaded["store_automation_secret"] is False  # default
    assert loaded["password"] == password_hash  # unchanged -- I don't know if this is intended
    assert loaded["enforce_pw_change"] is True

    with time_machine.travel(datetime.datetime.fromisoformat("2010-02-01 09:30:00Z")):
        updated_internal_attributes = _api_to_internal_format(
            _load_user(name),
            {"auth_option": {"auth_type": "remove"}},
            PasswordPolicy(12, None),
        )
        edit_users(
            {name: updated_internal_attributes},
            default_sites,
            get_user_attributes([]),
            use_git=False,
            acting_user=LoggedInSuperUser(),
        )

    loaded = _load_internal_attributes(name)
    assert "password" not in loaded  # password removed
    assert (
        loaded["last_pw_change"] == 1265014800
    )  # 09:00:00 -- no change from previous edit (secret unchanged)
    assert loaded["enforce_pw_change"] is True
    assert loaded["is_automation_user"] is False
    assert loaded["store_automation_secret"] is False


@managedtest
def test_openapi_managed_global_edition(clients: ClientRegistry, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("cmk.ccc.version.edition", lambda *args, **kw: version.Edition.ULTIMATEMT)

    with time_machine.travel(datetime.datetime.fromisoformat("2010-02-01 08:00:00Z")):
        resp = clients.User.create(username="user", fullname="Cosme Fulanito", customer="global")

    extensions = resp.json["extensions"]
    assert extensions["customer"] == "global"
    assert extensions["idle_timeout"] == {"option": "global"}


@managedtest
def test_managed_global_internal(
    monkeypatch: MonkeyPatch,
    request_context: None,
) -> None:
    # this test uses the internal mechanics of the user endpoint

    user_object: UserSpec = {
        "ui_theme": None,
        "ui_sidebar_position": None,
        "nav_hide_icons_title": None,
        "icons_per_item": None,
        "show_mode": None,
        "start_url": None,
        "force_authuser": False,
        "enforce_pw_change": False,
        "alias": "User Name",
        "locked": False,
        "pager": "",
        "roles": [],
        "contactgroups": [],
        "customer": None,  # None represents global internally
        "email": "",
        "fallback_contact": False,
        "disable_notifications": {},
    }
    create_user(
        UserId("user"),
        user_object,
        default_sites,
        get_user_attributes([]),
        use_git=False,
        acting_user=LoggedInSuperUser(),
    )
    user_internal = _load_user(UserId("user"))
    user_endpoint_attrs = complement_customer(_internal_to_api_format(user_internal))
    assert user_endpoint_attrs["customer"] == "global"


@managedtest
def test_global_full_configuration(clients: ClientRegistry) -> None:
    username = "cmkuser"

    with time_machine.travel(datetime.datetime.fromisoformat("2010-02-01 08:00:00Z")):
        clients.User.create(
            username=username,
            fullname="Mathias Kettner",
            customer="global",
            auth_option={"auth_type": "password", "password": "password1234"},
            disable_login=False,
            contact_options={"email": "user@example.com"},
            pager_address="",
            idle_timeout={"option": "global"},
            roles=["user"],
            disable_notifications={"disable": False},
            language="en",
            temperature_unit="fahrenheit",
        )

    resp = clients.User.get(username=username)

    assert resp.json["extensions"] == {
        "contact_options": {"email": "user@example.com", "fallback_contact": False},
        "disable_login": False,
        "fullname": "Mathias Kettner",
        "pager_address": "",
        "roles": ["user"],
        "contactgroups": [],
        "language": "en",
        "customer": "global",
        "idle_timeout": {"option": "global"},
        "disable_notifications": {},
        "auth_option": {"enforce_password_change": False, "auth_type": "password"},
        "interface_options": {
            "interface_theme": "default",
            "main_menu_icons": "topic",
            "mega_menu_icons": "topic",  # TODO: DEPRECATED(18295) remove "mega_menu_icons"
            "navigation_bar_icons": "hide",
            "show_mode": "default",
            "sidebar_position": "right",
            "contextual_help_icon": "show_icon",
        },
        "temperature_unit": "fahrenheit",
        "start_url": "default_start_url",
    }


def test_managed_idle_internal(
    with_automation_user: tuple[UserId, str],
    monkeypatch: MonkeyPatch,
) -> None:
    # this test uses the internal mechanics of the user endpoint
    username, _secret = with_automation_user

    user_object: UserSpec = {
        "ui_theme": None,
        "ui_sidebar_position": None,
        "nav_hide_icons_title": None,
        "icons_per_item": None,
        "show_mode": None,
        "start_url": None,
        "force_authuser": False,
        "enforce_pw_change": False,
        "alias": "User Name",
        "locked": False,
        "pager": "",
        "roles": [],
        "contactgroups": [],
        "customer": None,  # None represents global internally
        "email": "",
        "fallback_contact": False,
        "disable_notifications": {},
    }
    create_user(
        UserId("user"),
        user_object,
        default_sites,
        get_user_attributes([]),
        use_git=False,
        acting_user=LoggedInSuperUser(),
    )

    user_internal = _load_user(UserId("user"))
    user_endpoint_attrs = complement_customer(_internal_to_api_format(user_internal))
    assert "idle_timeout" not in _load_user(username)
    assert user_endpoint_attrs["idle_timeout"] == {"option": "global"}


@managedtest
def test_openapi_user_update_contact_options(clients: ClientRegistry) -> None:
    # this test uses the internal mechanics of the user endpoint

    username = "cmkuser"
    with time_machine.travel(datetime.datetime.fromisoformat("2010-02-01 08:00:00Z")):
        clients.User.create(
            username=username,
            fullname="Mathias Kettner",
            customer="global",
            auth_option={"auth_type": "password", "password": "password1234"},
            interface_options={
                "mega_menu_icons": "entry"
            },  # TODO: DEPRECATED(18295) remove "mega_menu_icons"
            disable_login=False,
            idle_timeout={"option": "global"},
            roles=["user"],
            disable_notifications={"disable": False},
            pager_address="",
            language="en",
        )

    clients.User.edit(
        username=username, contact_options={"fallback_contact": True}, expect_ok=False
    ).assert_status_code(400)

    resp = clients.User.get(username=username)

    assert resp.json["extensions"] == {
        "contact_options": {"email": "", "fallback_contact": False},
        "disable_login": False,
        "fullname": "Mathias Kettner",
        "idle_timeout": {"option": "global"},
        "pager_address": "",
        "roles": ["user"],
        "contactgroups": [],
        "language": "en",
        "customer": "global",
        "disable_notifications": {},
        "auth_option": {"enforce_password_change": False, "auth_type": "password"},
        "interface_options": {
            "interface_theme": "default",
            "main_menu_icons": "entry",  # TODO reset to "topic" (CMK-23667, Werk#18295)
            "mega_menu_icons": "entry",  # TODO: DEPRECATED(18295) remove "mega_menu_icons"
            "navigation_bar_icons": "hide",
            "show_mode": "default",
            "sidebar_position": "right",
            "contextual_help_icon": "show_icon",
        },
        "start_url": "default_start_url",
    }


# TODO: DEPRECATED(18295) remove "mega_menu_icons"
@managedtest
def test_openapi_user_update_fails_because_alias_and_field_set(clients: ClientRegistry) -> None:
    # this test uses the internal mechanics of the user endpoint
    username = "cmkuser"
    with time_machine.travel(datetime.datetime.fromisoformat("2010-02-01 08:00:00Z")):
        clients.User.create(
            username=username,
            fullname="Mathias Kettner",
            customer="global",
            auth_option={"auth_type": "password", "password": "password1234"},
            interface_options={"mega_menu_icons": "entry"},
            disable_login=False,
            idle_timeout={"option": "global"},
            roles=["user"],
            disable_notifications={"disable": False},
            pager_address="",
            language="en",
        )

    clients.User.edit(
        username=username,
        interface_options={"mega_menu_icons": "entry", "main_menu_icons": "topic"},
        expect_ok=False,
    ).assert_status_code(400)


# TODO: DEPRECATED(18295) remove "mega_menu_icons"
@managedtest
def test_openapi_user_create_fails_because_alias_and_field_set(
    clients: ClientRegistry,
) -> None:
    # this test uses the internal mechanics of the user endpoint
    username = "cmkuser"
    with time_machine.travel(datetime.datetime.fromisoformat("2010-02-01 08:00:00Z")):
        clients.User.create(
            username=username,
            fullname="Mathias Kettner",
            customer="global",
            auth_option={"auth_type": "password", "password": "password1234"},
            interface_options={
                "mega_menu_icons": "entry",
                "main_menu_icons": "topic",
            },  # TODO: DEPRECATED(18295) remove "mega_menu_icons"
            disable_login=False,
            idle_timeout={"option": "global"},
            roles=["user"],
            disable_notifications={"disable": False},
            pager_address="",
            language="en",
            expect_ok=False,
        ).assert_status_code(400)


@managedtest
def test_openapi_user_disable_notifications(
    clients: ClientRegistry, monkeypatch: MonkeyPatch
) -> None:
    username = "cmkuser"

    clients.User.create(
        username=username,
        fullname="Mathias Kettner",
        customer="global",
        disable_notifications={"disable": True},
    )

    resp = clients.User.get(username=username)

    assert resp.json["extensions"]["disable_notifications"] == {
        "disable": True,
    }

    resp = clients.User.edit(username=username, disable_notifications={"disable": False})
    assert resp.json["extensions"]["disable_notifications"] == {}


@managedtest
def test_show_all_users_with_no_email(clients: ClientRegistry, monkeypatch: MonkeyPatch) -> None:
    clients.User.create(username="internal_user", fullname="Internal", customer="global")

    # We remove all the contact information to mimic the no email case
    monkeypatch.setattr(
        "cmk.gui.userdb.store.load_contacts",
        lambda *args, **kwargs: {},
    )

    resp = clients.User.get_all()
    assert len(resp.json["value"]) == 2
    assert all("contact_options" not in user["extensions"] for user in resp.json["value"])


@managedtest
def test_user_enforce_password_change_option(
    clients: ClientRegistry, monkeypatch: MonkeyPatch
) -> None:
    username = "cmkuser"

    resp = clients.User.create(
        username=username,
        fullname="Mathias Kettner",
        customer="global",
        auth_option={
            "auth_type": "password",
            "password": "password1234",
            "enforce_password_change": True,
        },
    )

    assert resp.json["extensions"]["auth_option"]["enforce_password_change"] is True

    resp = clients.User.edit(
        username=username,
        auth_option={
            "auth_type": "password",
            "enforce_password_change": False,
        },
    )

    assert resp.json["extensions"]["auth_option"]["enforce_password_change"] is False


@managedtest
def test_response_schema_compatible_with_request_schema(
    clients: ClientRegistry, monkeypatch: MonkeyPatch
) -> None:
    username = "cmkuser"

    res = clients.User.create(
        username=username,
        fullname="Mathias kettner",
        customer="global",
        auth_option={
            "auth_type": "password",
            "password": "password1234",
            "enforce_password_change": True,
        },
    )

    clients.User.edit(username=username, extra=res.json["extensions"])


@managedtest
@patch(
    "cmk.gui.userdb.user_attributes.theme_choices",
    return_value=[("modern-dark", "Dark"), ("facelift", "Light")],
)
def test_user_interface_settings(_mock: None, clients: ClientRegistry) -> None:
    username = "cmkuser"

    resp = clients.User.create(
        username=username,
        fullname="Mathias Kettner",
        customer="global",
        interface_options={
            "interface_theme": "dark",
            "sidebar_position": "left",
            "navigation_bar_icons": "show",
            "main_menu_icons": "entry",
            "show_mode": "enforce_show_more",
        },
    )

    interface_options = resp.json["extensions"]["interface_options"]
    assert interface_options["interface_theme"] == "dark"
    assert interface_options["sidebar_position"] == "left"
    assert interface_options["navigation_bar_icons"] == "show"
    assert interface_options["main_menu_icons"] == "entry"
    # TODO: DEPRECATED(18295) remove "mega_menu_icons"
    assert interface_options["mega_menu_icons"] == "entry"
    assert interface_options["show_mode"] == "enforce_show_more"

    resp = clients.User.edit(username=username, interface_options={"interface_theme": "light"})
    assert resp.json["extensions"]["interface_options"]["interface_theme"] == "light"


def _random_string(size: int) -> str:
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(size))


def _load_internal_attributes(username: UserId) -> dict[str, Any]:
    user_attributes = _load_user(username)
    internal_attributes = {
        k: v
        for k, v in user_attributes.items()
        if k
        not in (
            "nav_hide_icons_title",
            "icons_per_item",
            "show_mode",
            "ui_theme",
            "ui_sidebar_position",
            "start_url",
            "force_authuser",
        )
    }
    return complement_customer(internal_attributes)


@managedtest
def test_openapi_new_user_with_cloned_role(
    clients: ClientRegistry, monkeypatch: MonkeyPatch
) -> None:
    cloned_role: UserRole = clone_role(RoleID("admin"), pprint_value=False)
    username = f"new_user_with_role_{cloned_role.name}"
    fullname = f"NewUser_{cloned_role.name}"

    res1 = clients.User.create(
        username=username, fullname=fullname, customer="provider", roles=[cloned_role.name]
    )
    assert res1.json["extensions"]["roles"] == [cloned_role.name]

    res2 = clients.User.edit(
        username=username,
        fullname=fullname,
        customer="provider",
        roles=["user", "guest"],
        etag="valid_etag",
    )
    assert res2.json["extensions"]["roles"] == ["user", "guest"]


@managedtest
def test_openapi_new_user_with_non_existing_role(clients: ClientRegistry) -> None:
    userrole = "non-existing-userole"
    clients.User.create(
        username=f"new_user_with_role_{userrole}",
        fullname=f"NewUser_{userrole}",
        customer="provider",
        roles=[userrole],
        expect_ok=False,
    ).assert_status_code(400)


@contextmanager
def custom_user_attributes_ctx(attrs: list[CustomUserAttrSpec]) -> Iterator:
    try:
        save_custom_attrs_to_mk_file({"user": attrs, "host": []})
        update_user_custom_attrs(get_user_attributes(attrs), datetime.datetime.today())
        yield
    finally:
        save_custom_attrs_to_mk_file({"user": attrs, "host": []})


def add_default_customer_in_managed_edition(params: dict[str, Any]) -> None:
    if version.edition(paths.omd_root) is version.Edition.ULTIMATEMT:
        params["customer"] = "global"


@managedtest
@patch(
    "cmk.gui.userdb.user_attributes.theme_choices",
    return_value=[("modern-dark", "Dark")],
)
def test_openapi_custom_attributes_of_user(
    _mock: None,
    clients: ClientRegistry,
    monkeypatch: MonkeyPatch,
) -> None:
    username = "rob_halford"

    # TODO: Ask what to do with attributes creation
    attr = CustomUserAttrSpec(
        {
            "name": "judas",
            "title": "judas",
            "help": "help",
            "topic": "basic",
            "type": "TextAscii",
            "show_in_table": False,
            "add_custom_macro": False,
            "user_editable": True,
        }
    )

    with custom_user_attributes_ctx([attr]):
        clients.User.create(
            username=username,
            fullname="Mathias Kettner",
            customer="provider",
            interface_options={
                "interface_theme": "dark",
                "sidebar_position": "left",
                "navigation_bar_icons": "show",
                "main_menu_icons": "entry",
                "show_mode": "enforce_show_more",
            },
            extra={
                "judas": "priest",
            },
        )

        result = clients.User.get(username=username)

        assert result.json["extensions"]["judas"] == "priest"


@managedtest
@patch(
    "cmk.gui.userdb.user_attributes.theme_choices",
    return_value=[("modern-dark", "Dark")],
)
def test_edit_custom_attributes_of_user(_mock: None, clients: ClientRegistry) -> None:
    username = "rob_halford"

    attr = CustomUserAttrSpec(
        {
            "name": "judas",
            "title": "judas",
            "help": "help",
            "topic": "basic",
            "type": "TextAscii",
            "show_in_table": False,
            "add_custom_macro": False,
            "user_editable": True,
        }
    )

    with custom_user_attributes_ctx([attr]):
        clients.User.create(
            username=username,
            fullname="Mathias Kettner",
            customer="provider",
            interface_options={
                "interface_theme": "dark",
                "sidebar_position": "left",
                "navigation_bar_icons": "show",
                "main_menu_icons": "entry",
                "show_mode": "enforce_show_more",
            },
            extra={
                "judas": "priest",
            },
        )

        resp = clients.User.get(username=username)
        assert resp.json["extensions"]["judas"] == "priest"

        resp2 = clients.User.edit(
            username=username,
            extra={"judas": "Iscariot"},
        )
        assert resp2.json["extensions"]["judas"] == "Iscariot"


@managedtest
def test_create_user_with_non_existing_custom_attribute(
    clients: ClientRegistry, monkeypatch: MonkeyPatch
) -> None:
    result = clients.User.create(
        username="cmkuser",
        fullname="Matias Kettner",
        customer="global",
        interface_options={
            "interface_theme": "dark",
            "sidebar_position": "left",
            "navigation_bar_icons": "show",
            "main_menu_icons": "entry",
            "show_mode": "enforce_show_more",
        },
        extra={
            "i_do_not": "exists",
        },
        expect_ok=False,
    )

    assert result.json["status"] == 400
    assert len(result.json["fields"]["_schema"]) == 1
    assert result.json["fields"]["_schema"][0] == "Unknown Attribute: 'i_do_not'"


@pytest.mark.parametrize(
    "username",
    [
        "!@#@%)@!#&)!@*#$",  # disallowed characters
        64 * "𐌈",  # too long
    ],
)
def test_user_with_invalid_id(clients: ClientRegistry, username: str) -> None:
    clients.User.create(
        username=username, fullname="Invalid name", expect_ok=False
    ).assert_status_code(400)


def test_openapi_edit_non_existing_user_regression(clients: ClientRegistry) -> None:
    clients.User.edit(
        "i_do_not_exists",
        fullname="I hopefully won't crash the site!",
        expect_ok=False,
    ).assert_status_code(404)


@managedtest
def test_openapi_all_authorized_sites(clients: ClientRegistry) -> None:
    clients.User.create(
        username="user1",
        fullname="User 1",
        authorized_sites=["all"],
        expect_ok=True,
        customer="provider",
    )
    clients.User.create(
        username="user2",
        fullname="User 2",
        authorized_sites=["NO_SITE"],
        expect_ok=True,
        customer="provider",
    )
    clients.User.edit(username="user2", fullname="User 2", authorized_sites=["all"], expect_ok=True)


@pytest.fixture(name="mock_users_config")
def fixture_mock_users_config(mocker: MockerFixture) -> None:
    user_cfg = Users(
        {
            "saml.user@example.com": {
                "alias": "Samler",
                "force_authuser": False,
                "roles": ["admin"],
                "connector": MOCK_SAML_CONNECTOR_NAME,
                "locked": False,
                "nav_hide_icons_title": None,
                "icons_per_item": None,
                "show_mode": None,
            },
        }
    )

    mocker.patch("cmk.gui.fields.definitions.load_users", return_value=user_cfg)
    mocker.patch("cmk.gui.openapi.endpoints.user_config.load_users", return_value=user_cfg)


@pytest.fixture(name="mock_user_connections_config")
def fixture_mock_user_connections_config(mocker: MockerFixture) -> MagicMock:
    """Mock the user connections config

    The type of a SAML user is determined by the users.mk file as well as the user_connections.mk
    file.

    """
    return mocker.patch(
        "cmk.gui.openapi.endpoints.user_config.load_connection_config",
        # not reflective of actual SAML connector
        return_value=[{"id": MOCK_SAML_CONNECTOR_NAME, "name": "bla", "type": "saml2"}],
    )


@pytest.mark.usefixtures("mock_users_config", "mock_user_connections_config")
def test_openapi_auth_type_of_saml_user(clients: ClientRegistry) -> None:
    """
    Notes:
         - A SAML user (currently) cannot be created via the REST API
         - Assume that the user is already created
    """
    resp = clients.User.get("saml.user@example.com")
    assert resp.json["extensions"]["auth_option"] == {"auth_type": ConnectorType.SAML2}


@managedtest
def test_user_without_permission_cant_interrogate_if_user_exists(clients: ClientRegistry) -> None:
    # Create a guest user using default client credentials
    clients.User.create(
        username="user1",
        fullname="user1",
        customer="provider",
        authorized_sites=["NO_SITE"],
        roles=["guest"],
        auth_option={"auth_type": "password", "password": "supersecretish1"},
    )

    # Set client credentials to new guest user
    clients.User.set_credentials("user1", "supersecretish1")

    # Attempt to create a new user using a guest user
    resp1 = clients.User.create(
        username="user2",
        fullname="user2",
        customer="provider",
        authorized_sites=["NO_SITE"],
        roles=["guest"],
        auth_option={"auth_type": "password", "password": "supersecretish2"},
        expect_ok=False,
    )
    resp1.assert_status_code(403)
    assert (
        resp1.json["detail"]
        == "We are sorry, but you lack the permission for this operation. If you do not like this then please ask your administrator to provide you with the following permission: '<b>User management</b>'."
    )

    # Attempt to edit a user using a guest user
    resp2 = clients.User.edit(
        username="user1",
        fullname="user1",
        authorized_sites=["all"],
        expect_ok=False,
    )
    resp2.assert_status_code(403)
    assert (
        resp2.json["detail"]
        == "We are sorry, but you lack the permission for this operation. If you do not like this then please ask your administrator to provide you with the following permission: '<b>User management</b>'."
    )

    # Attempt to delete a user using a guest user
    resp3 = clients.User.delete(
        username="user1",
        expect_ok=False,
    )
    resp3.assert_status_code(403)
    assert (
        resp3.json["detail"]
        == "We are sorry, but you lack the permission for this operation. If you do not like this then please ask your administrator to provide you with the following permission: '<b>User management</b>'."
    )


@managedtest
def test_delete_and_edit_user_when_client_user_has_permission_to_do_so(
    clients: ClientRegistry,
) -> None:
    clients.User.create(
        username="user1",
        fullname="user1",
        customer="provider",
        authorized_sites=["NO_SITE"],
        roles=["guest"],
        auth_option={"auth_type": "password", "password": "supersecretish1"},
    )
    clients.User.edit(
        username="user1",
        fullname="user1",
        authorized_sites=["all"],
    )
    clients.User.delete(username="user1")


@managedtest
def test_get_unknown_user(clients: ClientRegistry) -> None:
    clients.User.get(
        username="userA",
        expect_ok=False,
    ).assert_status_code(404)


@managedtest
def test_create_user_with_contact_group(clients: ClientRegistry) -> None:
    clients.ContactGroup.create(name="group_one", alias="Group")
    resp = clients.User.create(
        username="user",
        fullname="user",
        contactgroups=["group_non_existent"],
        expect_ok=False,
    )
    resp.assert_status_code(400)

    resp = clients.User.create(
        username="user",
        fullname="user",
        customer="provider",
        contactgroups=["group_one"],
    )
    assert resp.json["extensions"]["contactgroups"] == ["group_one"]


def test_openapi_minimum_configuration(clients: ClientRegistry) -> None:
    create_resp = clients.User.create(username="user", fullname="User Test")
    get_resp = clients.User.get(username="user")

    assert create_resp.json == get_resp.json
    assert create_resp.json["id"] == "user"
    assert create_resp.json["extensions"]["fullname"] == "User Test"


def test_openapi_full_configuration(clients: ClientRegistry) -> None:
    clients.ContactGroup.create(name="group_one", alias="Group")
    create_resp = clients.User.create(
        username="user",
        fullname="User Test",
        authorized_sites=["NO_SITE"],
        contactgroups=["group_one"],
        temperature_unit="fahrenheit",
        disable_login=True,
        pager_address="LMP",
        language="de",
        contact_options={"email": "test@example.com", "fallback_contact": True},
        auth_option={"auth_type": "automation", "secret": "TopSecret!"},
        roles=["guest"],
    )

    get_resp = clients.User.get(username="user")

    assert create_resp.json == get_resp.json


def test_openapi_user_dismiss_warning(clients: ClientRegistry) -> None:
    clients.User.dismiss_warning(warning="notification_fallback")
    assert user.dismissed_warnings == {"notification_fallback"}


@managedtest
def test_openapi_edit_user_should_not_modify_start_url(clients: ClientRegistry) -> None:
    username = "user_1"
    clients.User.create(
        username=username,
        fullname="User Test",
        start_url="welcome_page",
    )
    assert (
        clients.User.edit(
            username=username,
            fullname="User Test Updated",
        ).json["extensions"]["start_url"]
        == "welcome_page"
    )


@managedtest
def test_openapi_create_user_edit_start_url(clients: ClientRegistry) -> None:
    username = "user_2"
    assert (
        clients.User.create(
            username=username,
            fullname="User Test",
        ).json["extensions"]["start_url"]
        == "default_start_url"
    )

    assert (
        clients.User.edit(
            username=username,
            fullname="User Test Updated",
            start_url="welcome_page",
        ).json["extensions"]["start_url"]
        == "welcome_page"
    )

    assert (
        clients.User.edit(
            username=username,
            fullname="User Test Updated Again",
            start_url="some_custom_url",
        ).json["extensions"]["start_url"]
        == "some_custom_url"
    )
