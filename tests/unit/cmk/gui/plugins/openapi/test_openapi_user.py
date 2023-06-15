#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
import json
import random
import string
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from typing import Any, ContextManager
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time
from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from tests.testlib.rest_api_client import ClientRegistry

from tests.unit.cmk.gui.conftest import SetConfig, WebTestAppForCMK

from cmk.utils import version
from cmk.utils.crypto.password import PasswordHash
from cmk.utils.user import UserId

from cmk.gui import userdb
from cmk.gui.config import active_config
from cmk.gui.plugins.openapi.endpoints.user_config import (
    _api_to_internal_format,
    _internal_to_api_format,
    _load_user,
)
from cmk.gui.plugins.openapi.endpoints.utils import complement_customer
from cmk.gui.plugins.userdb.utils import ConnectorType
from cmk.gui.type_defs import UserObject, UserRole
from cmk.gui.watolib.custom_attributes import save_custom_attrs_to_mk_file, update_user_custom_attrs
from cmk.gui.watolib.userroles import clone_role, RoleID
from cmk.gui.watolib.users import edit_users

managedtest = pytest.mark.skipif(not version.is_managed_edition(), reason="see #7213")

MOCK_SAML_CONNECTOR_NAME = "saml_connector"


@managedtest
def test_idle_timeout(aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch: MonkeyPatch) -> None:
    user_detail = {
        "username": "user",
        "fullname": "User Name",
        "customer": "global",
        "idle_timeout": {"option": "individual", "duration": 666},
    }

    base = "/NO_SITE/check_mk/api/1.0"
    with freeze_time("2010-02-01 08:00:00"):
        resp = aut_user_auth_wsgi_app.call_method(
            "post",
            base + "/domain-types/user_config/collections/all",
            params=json.dumps(user_detail),
            headers={"Accept": "application/json"},
            status=200,
            content_type="application/json",
        )

    assert resp.json_body["extensions"]["idle_timeout"]["duration"] == 666

    resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/user_config/user",
        params=json.dumps({"idle_timeout": {"option": "individual", "duration": 999}}),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )
    assert resp.json_body["extensions"]["idle_timeout"]["duration"] == 999

    resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/user_config/user",
        params=json.dumps({"idle_timeout": {"option": "disable"}}),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )
    assert resp.json_body["extensions"]["idle_timeout"]["option"] == "disable"


@managedtest
def test_openapi_customer(
    aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch: MonkeyPatch
) -> None:
    user_detail = {
        "username": "user",
        "fullname": "User Name",
        "customer": "global",
    }

    base = "/NO_SITE/check_mk/api/1.0"
    with freeze_time("2010-02-01 08:00:00"):
        resp = aut_user_auth_wsgi_app.call_method(
            "post",
            base + "/domain-types/user_config/collections/all",
            params=json.dumps(user_detail),
            headers={"Accept": "application/json"},
            status=200,
            content_type="application/json",
        )

    assert resp.json_body["extensions"] == {
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
            "mega_menu_icons": "topic",
            "navigation_bar_icons": "hide",
            "show_mode": "default",
            "sidebar_position": "right",
        },
    }

    resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/user_config/user",
        params=json.dumps({"customer": "provider"}),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )
    assert resp.json_body["extensions"]["customer"] == "provider"


@managedtest
def test_openapi_user_minimal_settings(
    monkeypatch: MonkeyPatch, run_as_superuser: Callable[[], ContextManager[None]]
) -> None:
    with freeze_time("2021-09-24 12:36:00"), run_as_superuser():
        user_object: UserObject = {
            UserId("user"): {
                "attributes": {
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
                },
                "is_new_user": True,
            }
        }
        edit_users(user_object)

    user_attributes = _load_internal_attributes(UserId("user"))

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
        "last_pw_change": 1632486960,
        "num_failed_logins": 0,
        "serial": 0,
    }


@managedtest
def test_openapi_user_minimal_password_settings(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    monkeypatch: MonkeyPatch,
) -> None:
    user_detail = {
        "username": "user",
        "fullname": "User Name",
        "customer": "provider",
        "auth_option": {
            "auth_type": "password",
            "password": "password1234",
            "enforce_password_change": True,
        },
    }

    base = "/NO_SITE/check_mk/api/1.0"
    with freeze_time("2010-02-01 08:00:00"):
        resp = aut_user_auth_wsgi_app.call_method(
            "post",
            base + "/domain-types/user_config/collections/all",
            params=json.dumps(user_detail),
            headers={"Accept": "application/json"},
            status=200,
            content_type="application/json",
        )
    extensions = resp.json_body["extensions"]
    assert extensions["customer"] == "provider"
    assert extensions["auth_option"]["enforce_password_change"] is True
    assert "last_pw_change" not in extensions
    assert "password" not in extensions

    user_from_db = userdb.load_user(UserId(resp.json["id"]))
    assert user_from_db["connector"]
    assert user_from_db["connector"] == "htpasswd"

    edit_details = {
        "auth_option": {
            "auth_type": "automation",
            "secret": "SOMEAUTOMATION",
        },
        "roles": ["user"],
        "idle_timeout": {"option": "disable"},
    }
    with freeze_time("2010-02-01 08:30:00"):
        resp = aut_user_auth_wsgi_app.call_method(
            "put",
            base + "/objects/user_config/user",
            params=json.dumps(edit_details),
            status=200,
            headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
            content_type="application/json",
        )

    extensions = resp.json_body["extensions"]
    assert extensions["auth_option"] == {"auth_type": "automation"}
    assert extensions["idle_timeout"]["option"] == "disable"
    assert extensions["roles"] == ["user"]

    user_from_db = userdb.load_user(UserId(resp.json["id"]))
    assert user_from_db["connector"]
    assert user_from_db["connector"] == "htpasswd"


def test_openapi_all_users(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/user_config/collections/all",
        status=200,
        headers={"Accept": "application/json"},
    )
    users = resp.json_body["value"]
    assert len(users) == 1

    _user_resp = aut_user_auth_wsgi_app.call_method(
        "get", users[0]["links"][0]["href"], status=200, headers={"Accept": "application/json"}
    )


@managedtest
def test_openapi_user_config(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    with_automation_user: tuple[UserId, str],
    monkeypatch: MonkeyPatch,
) -> None:
    name = _random_string(10)
    alias = "KPECYCq79E"

    user_detail = {
        "username": name,
        "fullname": alias,
        "customer": "provider",
        "disable_notifications": {
            "timerange": {"start_time": "2020-01-01T00:00:00Z", "end_time": "2020-01-02T00:00:00Z"}
        },
    }

    base = "/NO_SITE/check_mk/api/1.0"
    with freeze_time("2010-02-01 08:30:00"):
        _resp = aut_user_auth_wsgi_app.call_method(
            "post",
            base + "/domain-types/user_config/collections/all",
            params=json.dumps(user_detail),
            headers={"Accept": "application/json"},
            status=200,
            content_type="application/json",
        )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + f"/objects/user_config/{name}",
        headers={"Accept": "application/json"},
        status=200,
    )

    extensions = resp.json_body["extensions"]
    assert extensions["disable_notifications"] == {
        "timerange": {
            "end_time": "2020-01-02T00:00:00+00:00",
            "start_time": "2020-01-01T00:00:00+00:00",
        }
    }

    collection_resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/user_config/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert len(collection_resp.json_body["value"]) == 2

    _resp = aut_user_auth_wsgi_app.call_method(
        "delete",
        base + f"/objects/user_config/{name}",
        status=204,
        headers={"Accept": "application/json", "If-Match": resp.headers["Etag"]},
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + f"/objects/user_config/{name}",
        headers={"Accept": "application/json"},
        status=404,
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/user_config/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert len(resp.json_body["value"]) == 1


@managedtest
def test_openapi_user_internal_with_notifications(
    monkeypatch: MonkeyPatch, run_as_superuser: Callable[[], ContextManager[None]]
) -> None:
    name = UserId(_random_string(10))

    user_object: UserObject = {
        name: {
            "attributes": {
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
            },
            "is_new_user": True,
        }
    }
    with run_as_superuser():
        edit_users(user_object)

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
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    monkeypatch: MonkeyPatch,
    base: str,
    test_data: Mapping[str, str],
    expected_serial_count: int,
) -> None:
    name = _random_string(10)
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/user_config/collections/all",
        params=json.dumps({"username": name, "fullname": "KPECYCq79E", "customer": "provider"}),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    user_data = resp.json["extensions"]
    user_data.pop("auth_option", None)

    if test_data is not None:
        user_data.update(test_data)

    resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + f"/objects/user_config/{name}",
        params=json.dumps(user_data),
        status=200,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )

    serial_count_after = _load_user(UserId(name))["serial"]
    assert serial_count_after == expected_serial_count


@managedtest
def test_openapi_user_edit_auth(
    aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch: MonkeyPatch
) -> None:
    name = "foo"
    alias = "Foo Bar"

    user_detail = {
        "username": name,
        "fullname": alias,
        "customer": "provider",
        "roles": ["user"],
        "auth_option": {"auth_type": "password", "password": "password1234"},
    }

    base = "/NO_SITE/check_mk/api/1.0"
    with freeze_time("2010-02-01 08:00:00"):
        resp = aut_user_auth_wsgi_app.call_method(
            "post",
            base + "/domain-types/user_config/collections/all",
            params=json.dumps(user_detail),
            headers={"Accept": "application/json"},
            status=200,
            content_type="application/json",
        )
    extensions = resp.json_body["extensions"]
    assert extensions["customer"] == "provider"
    assert extensions["auth_option"]["enforce_password_change"] is False

    edit_details = {
        "auth_option": {"auth_type": "automation", "secret": "QWXWBFUCSUOXNCPJUMS@"},
    }

    with freeze_time("2010-02-01 08:30:00"):
        resp = aut_user_auth_wsgi_app.call_method(
            "put",
            base + "/objects/user_config/foo",
            params=json.dumps(edit_details),
            status=200,
            headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
            content_type="application/json",
        )

    remove_details = {
        "auth_option": {
            "auth_type": "remove",
        },
    }
    with freeze_time("2010-02-01 09:00:00"):
        _resp = aut_user_auth_wsgi_app.call_method(
            "put",
            base + "/objects/user_config/foo",
            params=json.dumps(remove_details),
            status=200,
            headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
            content_type="application/json",
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
    aut_user_auth_wsgi_app: WebTestAppForCMK, with_password_policy: None, password: str, reason: str
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

    base = "/NO_SITE/check_mk/api/1.0"
    response = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/user_config/collections/all",
        params=json.dumps(user_detail),
        headers={"Accept": "application/json"},
        status=400,
        content_type="application/json",
    )
    assert reason in response.json["detail"]


def test_openapi_automation_enforce_pw_change(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
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

    base = "/NO_SITE/check_mk/api/1.0"
    response = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/user_config/collections/all",
        params=json.dumps(user_detail),
        headers={"Accept": "application/json"},
        status=400,
        content_type="application/json",
    )
    assert '"enforce_password_change": ["Unknown field."]' in response


@pytest.mark.parametrize("auth_type", ["password", "automation"])
def test_openapi_incomplete_auth_options(
    aut_user_auth_wsgi_app: WebTestAppForCMK, auth_type: str
) -> None:
    """Test that new users cannot be created without a password / secret"""

    user_detail = complement_customer(
        {
            "username": f"incomplete_auth_options_{auth_type}",
            "fullname": "a new user",
            "roles": ["user"],
            "auth_option": {"auth_type": auth_type},
        }
    )

    base = "/NO_SITE/check_mk/api/1.0"
    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/user_config/collections/all",
        params=json.dumps(user_detail),
        headers={"Accept": "application/json"},
        status=400,
        content_type="application/json",
    )


@managedtest
def test_openapi_user_internal_auth_handling(
    monkeypatch: MonkeyPatch, run_as_superuser: Callable[[], ContextManager[None]]
) -> None:
    monkeypatch.setattr(
        "cmk.gui.userdb.htpasswd.hash_password",
        lambda x: "$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C",
    )

    name = UserId("foo")

    user_object: UserObject = {
        name: {
            "attributes": {
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
                "password": PasswordHash(
                    "$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C"
                ),
                "last_pw_change": 1265011200,  # 2010-02-01 08:00:00
                "serial": 1,
                "disable_notifications": {},
            },
            "is_new_user": True,
        }
    }

    with freeze_time("2010-02-01 08:30:00"):
        with run_as_superuser():
            edit_users(user_object)

    assert _load_internal_attributes(name) == {
        "alias": "Foo Bar",
        "customer": "provider",
        "email": "",
        "pager": "",
        "contactgroups": [],
        "fallback_contact": False,
        "disable_notifications": {},
        "user_scheme_serial": 1,
        "locked": False,
        "roles": ["user"],
        "password": "$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C",
        "serial": 1,
        "last_pw_change": 1265011200,  # 08:00:00 -- uses creation data, not current time
        "enforce_pw_change": True,
        "num_failed_logins": 0,
    }

    with freeze_time("2010-02-01 09:00:00"):
        updated_internal_attributes = _api_to_internal_format(
            _load_user(name),
            {"auth_option": {"secret": "QWXWBFUCSUOXNCPJUMS@", "auth_type": "automation"}},
        )
        with run_as_superuser():
            edit_users(
                {
                    name: {
                        "attributes": updated_internal_attributes,
                        "is_new_user": False,
                    }
                }
            )

    assert _load_internal_attributes(name) == {
        "alias": "Foo Bar",
        "customer": "provider",
        "email": "",
        "pager": "",
        "contactgroups": [],
        "fallback_contact": False,
        "disable_notifications": {},
        "user_scheme_serial": 1,
        "locked": False,
        "roles": ["user"],
        "automation_secret": "QWXWBFUCSUOXNCPJUMS@",
        "password": "$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C",
        "serial": 1,  # this is 2 internally but the function is not invoked here
        "last_pw_change": 1265014800,  # 09:00:00 -- changed as secret was changed
        "enforce_pw_change": True,
        "num_failed_logins": 0,
        "connector": "htpasswd",
    }

    with freeze_time("2010-02-01 09:30:00"):
        updated_internal_attributes = _api_to_internal_format(
            _load_user(name), {"auth_option": {"auth_type": "remove"}}
        )
        with run_as_superuser():
            edit_users(
                {
                    name: {
                        "attributes": updated_internal_attributes,
                        "is_new_user": False,
                    }
                }
            )
    assert _load_internal_attributes(name) == {
        "alias": "Foo Bar",
        "customer": "provider",
        "email": "",
        "pager": "",
        "contactgroups": [],
        "fallback_contact": False,
        "disable_notifications": {},
        "user_scheme_serial": 1,
        "locked": False,
        "roles": ["user"],
        "serial": 1,
        "last_pw_change": 1265014800,  # 09:00:00 -- no change from previous edit (secret unchanged)
        "enforce_pw_change": True,
        "num_failed_logins": 0,
        "connector": "htpasswd",
    }


@managedtest
def test_openapi_managed_global_edition(
    aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr("cmk.utils.version.is_managed_edition", lambda: True)

    user_detail = {
        "username": "user",
        "fullname": "User Name",
        "customer": "global",
    }

    base = "/NO_SITE/check_mk/api/1.0"
    with freeze_time("2010-02-01 08:00:00"):
        resp = aut_user_auth_wsgi_app.call_method(
            "post",
            base + "/domain-types/user_config/collections/all",
            params=json.dumps(user_detail),
            headers={"Accept": "application/json"},
            status=200,
            content_type="application/json",
        )

    extensions = resp.json["extensions"]
    assert extensions["customer"] == "global"
    assert extensions["idle_timeout"] == {"option": "global"}


@managedtest
def test_managed_global_internal(
    monkeypatch: MonkeyPatch, run_as_superuser: Callable[[], ContextManager[None]]
) -> None:
    # this test uses the internal mechanics of the user endpoint

    user_object: UserObject = {
        UserId("user"): {
            "attributes": {
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
            },
            "is_new_user": True,
        }
    }
    with run_as_superuser():
        edit_users(user_object)
    user_internal = _load_user(UserId("user"))
    user_endpoint_attrs = complement_customer(_internal_to_api_format(user_internal))
    assert user_endpoint_attrs["customer"] == "global"


@managedtest
def test_global_full_configuration(
    aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch: MonkeyPatch
) -> None:
    # this test uses the internal mechanics of the user endpoint

    user_detail = {
        "username": "cmkuser",
        "fullname": "Mathias Kettner",
        "customer": "global",
        "auth_option": {"auth_type": "password", "password": "password1234"},
        "disable_login": False,
        "contact_options": {"email": "user@example.com"},
        "pager_address": "",
        "idle_timeout": {"option": "global"},
        "roles": ["user"],
        "disable_notifications": {"disable": False},
        "language": "en",
        "temperature_unit": "fahrenheit",
    }

    base = "/NO_SITE/check_mk/api/1.0"
    with freeze_time("2010-02-01 08:00:00"):
        _resp = aut_user_auth_wsgi_app.call_method(
            "post",
            base + "/domain-types/user_config/collections/all",
            params=json.dumps(user_detail),
            headers={"Accept": "application/json"},
            status=200,
            content_type="application/json",
        )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/user_config/cmkuser",
        headers={"Accept": "application/json"},
        status=200,
    )

    assert resp.json_body["extensions"] == {
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
            "mega_menu_icons": "topic",
            "navigation_bar_icons": "hide",
            "show_mode": "default",
            "sidebar_position": "right",
        },
        "temperature_unit": "fahrenheit",
    }


def test_managed_idle_internal(
    with_automation_user: tuple[UserId, str],
    monkeypatch: MonkeyPatch,
    run_as_superuser: Callable[[], ContextManager[None]],
) -> None:
    # this test uses the internal mechanics of the user endpoint
    username, _secret = with_automation_user

    user_object: UserObject = {
        UserId("user"): {
            "attributes": {
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
            },
            "is_new_user": True,
        }
    }
    with run_as_superuser():
        edit_users(user_object)

    user_internal = _load_user(UserId("user"))
    user_endpoint_attrs = complement_customer(_internal_to_api_format(user_internal))
    assert "idle_timeout" not in _load_user(username)
    assert user_endpoint_attrs["idle_timeout"] == {"option": "global"}


@managedtest
def test_openapi_user_update_contact_options(
    aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch: MonkeyPatch
) -> None:
    # this test uses the internal mechanics of the user endpoint

    user_detail = {
        "username": "cmkuser",
        "fullname": "Mathias Kettner",
        "customer": "global",
        "auth_option": {"auth_type": "password", "password": "password1234"},
        "disable_login": False,
        "pager_address": "",
        "idle_timeout": {"option": "global"},
        "roles": ["user"],
        "disable_notifications": {"disable": False},
        "language": "en",
    }

    base = "/NO_SITE/check_mk/api/1.0"
    with freeze_time("2010-02-01 08:00:00"):
        resp = aut_user_auth_wsgi_app.call_method(
            "post",
            base + "/domain-types/user_config/collections/all",
            params=json.dumps(user_detail),
            headers={"Accept": "application/json"},
            status=200,
            content_type="application/json",
        )

    _ = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/user_config/cmkuser",
        params=json.dumps({"contact_options": {"fallback_contact": True}}),
        status=400,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/user_config/cmkuser",
        status=200,
        headers={"Accept": "application/json"},
    )

    assert resp.json_body["extensions"] == {
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
            "mega_menu_icons": "topic",
            "navigation_bar_icons": "hide",
            "show_mode": "default",
            "sidebar_position": "right",
        },
    }


@managedtest
def test_openapi_user_disable_notifications(
    aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch: MonkeyPatch
) -> None:
    # this test uses the internal mechanics of the user endpoint

    user_detail = {
        "username": "cmkuser",
        "fullname": "Mathias Kettner",
        "customer": "global",
        "disable_notifications": {"disable": True},
    }

    base = "/NO_SITE/check_mk/api/1.0"
    with freeze_time("2010-02-01 08:00:00"):
        _resp = aut_user_auth_wsgi_app.call_method(
            "post",
            base + "/domain-types/user_config/collections/all",
            params=json.dumps(user_detail),
            headers={"Accept": "application/json"},
            status=200,
            content_type="application/json",
        )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/user_config/cmkuser",
        status=200,
        headers={"Accept": "application/json"},
    )
    assert resp.json_body["extensions"]["disable_notifications"] == {
        "disable": True,
    }

    resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/user_config/cmkuser",
        params=json.dumps({"disable_notifications": {"disable": False}}),
        status=200,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )
    assert resp.json_body["extensions"]["disable_notifications"] == {}


@managedtest
def test_show_all_users_with_no_email(
    aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch: MonkeyPatch
) -> None:
    """Test a user which has no email internally similar to the internal cmkadmin user"""
    user_detail = {
        "username": "internal_user",
        "fullname": "Internal",
        "customer": "global",
    }

    base = "/NO_SITE/check_mk/api/1.0"
    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/user_config/collections/all",
        params=json.dumps(user_detail),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    # We remove all the contact information to mimic the no email case
    monkeypatch.setattr(
        "cmk.gui.userdb.store.load_contacts",
        lambda: {},
    )
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/user_config/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert len(resp.json["value"]) == 2
    assert all("contact_options" not in user["extensions"] for user in resp.json["value"])


@managedtest
def test_user_enforce_password_change_option(
    aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch: MonkeyPatch
) -> None:
    """Test enforce password change option for create and update endpoints"""

    user_detail = {
        "username": "cmkuser",
        "fullname": "Mathias Kettner",
        "customer": "global",
        "auth_option": {
            "auth_type": "password",
            "password": "password1234",
            "enforce_password_change": True,
        },
    }

    base = "/NO_SITE/check_mk/api/1.0"
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/user_config/collections/all",
        params=json.dumps(user_detail),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )
    assert resp.json["extensions"]["auth_option"]["enforce_password_change"] is True

    edit_details = {
        "auth_option": {
            "auth_type": "password",
            "enforce_password_change": False,
        }
    }
    update_resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/user_config/cmkuser",
        params=json.dumps(edit_details),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )
    assert update_resp.json_body["extensions"]["auth_option"]["enforce_password_change"] is False


@managedtest
def test_response_schema_compatible_with_request_schema(
    aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch: MonkeyPatch
) -> None:
    user_detail = {
        "username": "cmkuser",
        "fullname": "Mathias Kettner",
        "customer": "global",
        "auth_option": {
            "auth_type": "password",
            "password": "password1234",
            "enforce_password_change": True,
        },
    }

    base = "/NO_SITE/check_mk/api/1.0"
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/user_config/collections/all",
        params=json.dumps(user_detail),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/user_config/cmkuser",
        params=json.dumps(resp.json["extensions"]),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )


@managedtest
def test_user_interface_settings(
    aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch: MonkeyPatch
) -> None:
    """Test enforce password change option for create and update endpoints"""
    user_detail = {
        "username": "cmkuser",
        "fullname": "Mathias Kettner",
        "customer": "global",
        "interface_options": {
            "interface_theme": "dark",
            "sidebar_position": "left",
            "navigation_bar_icons": "show",
            "mega_menu_icons": "entry",
            "show_mode": "enforce_show_more",
        },
    }

    base = "/NO_SITE/check_mk/api/1.0"
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/user_config/collections/all",
        params=json.dumps(user_detail),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )
    interface_options = resp.json["extensions"]["interface_options"]
    assert interface_options["interface_theme"] == "dark"
    assert interface_options["sidebar_position"] == "left"
    assert interface_options["navigation_bar_icons"] == "show"
    assert interface_options["mega_menu_icons"] == "entry"
    assert interface_options["show_mode"] == "enforce_show_more"

    resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/user_config/cmkuser",
        params=json.dumps({"interface_options": {"interface_theme": "light"}}),
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        status=200,
        content_type="application/json",
    )
    assert resp.json["extensions"]["interface_options"]["interface_theme"] == "light"


def _random_string(size: int) -> str:
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(size))


def _load_internal_attributes(username: UserId) -> object:
    return complement_customer(_internal_attributes(_load_user(username)))


def _internal_attributes(user_attributes):
    return {
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


@managedtest
def test_openapi_new_user_with_cloned_role(
    base: str, aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch: MonkeyPatch
) -> None:
    cloned_role: UserRole = clone_role(RoleID("admin"))

    user_detail = {
        "username": f"new_user_with_role_{cloned_role.name}",
        "fullname": f"NewUser_{cloned_role.name}",
        "customer": "provider",
        "roles": [cloned_role.name],
    }

    resp1 = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/user_config/collections/all",
        params=json.dumps(user_detail),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    assert resp1.json["extensions"]["roles"] == [cloned_role.name]

    resp2 = aut_user_auth_wsgi_app.call_method(
        "put",
        base + f"/objects/user_config/new_user_with_role_{cloned_role.name}",
        params=json.dumps({"roles": ["user", "guest"]}),
        status=200,
        content_type="application/json",
        headers={"Accept": "application/json", "If-Match": resp1.headers["Etag"]},
    )

    assert resp2.json["extensions"]["roles"] == ["user", "guest"]


@managedtest
def test_openapi_new_user_with_non_existing_role(
    base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
) -> None:
    userrole = "non-existing-userole"
    user_detail = {
        "username": f"new_user_with_role_{userrole}",
        "fullname": f"NewUser_{userrole}",
        "customer": "provider",
        "roles": [userrole],
    }

    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/user_config/collections/all",
        params=json.dumps(user_detail),
        headers={"Accept": "application/json"},
        status=400,
        content_type="application/json",
    )


@contextmanager
def custom_user_attributes_ctx(attrs: list[Mapping[str, str | bool]]) -> Iterator:
    try:
        save_custom_attrs_to_mk_file({"user": attrs})
        update_user_custom_attrs(datetime.datetime.today())
        yield
    finally:
        save_custom_attrs_to_mk_file({})


def add_default_customer_in_managed_edition(params: dict[str, Any]) -> None:
    if version.is_managed_edition():
        params["customer"] = "global"


def test_openapi_custom_attributes_of_user(
    base: str,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    monkeypatch: MonkeyPatch,
) -> None:
    attr: Mapping[str, str | bool] = {
        "name": "judas",
        "title": "judas",
        "help": "help",
        "topic": "basic",
        "type": "TextAscii",
        "user_editable": True,
    }

    user = "rob_halford"
    params = {
        "username": user,
        "fullname": "Mathias Kettner",
        "interface_options": {
            "interface_theme": "dark",
            "sidebar_position": "left",
            "navigation_bar_icons": "show",
            "mega_menu_icons": "entry",
            "show_mode": "enforce_show_more",
        },
        "judas": "priest",
    }

    add_default_customer_in_managed_edition(params)

    with custom_user_attributes_ctx([attr]):
        aut_user_auth_wsgi_app.post(
            url=f"{base}/domain-types/user_config/collections/all",
            status=200,
            headers={"Accept": "application/json"},
            content_type="application/json",
            params=json.dumps(params),
        )

        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            f"{base}/objects/user_config/{user}",
            status=200,
            headers={"Accept": "application/json"},
        )
        assert resp.json["extensions"]["judas"] == "priest"


def test_create_user_with_non_existing_custom_attribute(
    base: str, aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch: MonkeyPatch
) -> None:
    params = {
        "username": "cmkuser",
        "fullname": "Mathias Kettner",
        "interface_options": {
            "interface_theme": "dark",
            "sidebar_position": "left",
            "navigation_bar_icons": "show",
            "mega_menu_icons": "entry",
            "show_mode": "enforce_show_more",
        },
        "i_do_not": "exists",
    }

    add_default_customer_in_managed_edition(params)

    aut_user_auth_wsgi_app.post(
        url=f"{base}/domain-types/user_config/collections/all",
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json",
        params=json.dumps(params),
    )


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
        "i_do_not_exists", fullname="I hopefully won't crash the site!", expect_ok=False
    ).assert_status_code(404)


def test_openapi_all_authorized_sites(clients: ClientRegistry) -> None:
    clients.User.create(
        username="user1", fullname="User 1", authorized_sites=["all"], expect_ok=True
    )
    clients.User.create(
        username="user2", fullname="User 2", authorized_sites=["NO_SITE"], expect_ok=True
    )
    clients.User.edit(username="user2", fullname="User 2", authorized_sites=["all"], expect_ok=True)


@pytest.fixture(name="mock_users_config")
def fixture_mock_users_config(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "cmk.gui.userdb.load_users",
        return_value={
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
        },
    )


@pytest.fixture(name="mock_user_connections_config")
def fixture_mock_user_connections_config(mocker: MockerFixture) -> MagicMock:
    """Mock the user connections config

    The type of a SAML user is determined by the users.mk file as well as the user_connections.mk
    file.

    """
    return mocker.patch(
        "cmk.gui.plugins.userdb.utils.load_connection_config",
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
