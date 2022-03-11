#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import random
import string

import pytest
from freezegun import freeze_time
from pytest import MonkeyPatch

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils import version
from cmk.utils.type_defs import UserId

from cmk.gui.plugins.openapi.endpoints.user_config import (
    _api_to_internal_format,
    _internal_to_api_format,
    _load_user,
)
from cmk.gui.plugins.openapi.endpoints.utils import complement_customer
from cmk.gui.watolib.users import edit_users

managedtest = pytest.mark.skipif(not version.is_managed_edition(), reason="see #7213")


@managedtest
def test_openapi_customer(aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch):
    monkeypatch.setattr(
        "cmk.gui.watolib.global_settings.rulebased_notifications_enabled", lambda: True
    )

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
        "enforce_password_change": False,
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
def test_openapi_user_minimal_settings(monkeypatch, run_as_superuser):
    monkeypatch.setattr(
        "cmk.gui.watolib.global_settings.rulebased_notifications_enabled", lambda: True
    )

    with freeze_time("2021-09-24 12:36:00"), run_as_superuser():
        edit_users(
            {
                "user": {
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
        )

    user_attributes = _load_internal_attributes("user")

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
        "user_scheme_serial": 0,
        "last_pw_change": 1632486960,
        "num_failed_logins": 0,
        "serial": 0,
    }


@managedtest
def test_openapi_user_minimal_password_settings(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    monkeypatch,
):
    monkeypatch.setattr(
        "cmk.gui.watolib.global_settings.rulebased_notifications_enabled", lambda: True
    )

    user_detail = {
        "username": "user",
        "fullname": "User Name",
        "customer": "provider",
        "auth_option": {
            "auth_type": "password",
            "password": "password",
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
    assert extensions["enforce_password_change"] is True
    assert "last_pw_change" not in extensions
    assert "password" not in extensions

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
    assert extensions["enforce_password_change"] is True
    assert extensions["idle_timeout"]["option"] == "disable"
    assert extensions["roles"] == ["user"]


def test_openapi_all_users(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))
    base = "/NO_SITE/check_mk/api/1.0"

    resp = wsgi_app.call_method(
        "get",
        base + "/domain-types/user_config/collections/all",
        status=200,
        headers={"Accept": "application/json"},
    )
    users = resp.json_body["value"]
    assert len(users) == 1

    _user_resp = wsgi_app.call_method(
        "get", users[0]["links"][0]["href"], status=200, headers={"Accept": "application/json"}
    )


@managedtest
def test_openapi_user_config(
    aut_user_auth_wsgi_app: WebTestAppForCMK, with_automation_user, monkeypatch
):
    monkeypatch.setattr(
        "cmk.gui.watolib.global_settings.rulebased_notifications_enabled", lambda: True
    )

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
def test_openapi_user_internal_with_notifications(monkeypatch, run_as_superuser):
    monkeypatch.setattr(
        "cmk.gui.watolib.global_settings.rulebased_notifications_enabled", lambda: True
    )

    name = _random_string(10)

    user_data = {
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
                "password": "$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C",
                "last_pw_change": 1265013000,
                "serial": 1,
                "disable_notifications": {"timerange": (1577836800.0, 1577923200.0)},
            },
            "is_new_user": True,
        }
    }
    with run_as_superuser():
        edit_users(user_data)

    assert _load_internal_attributes(name) == {
        "alias": "KPECYCq79E",
        "customer": "provider",
        "pager": "",
        "contactgroups": [],
        "email": "",
        "fallback_contact": False,
        "disable_notifications": {"timerange": (1577836800.0, 1577923200.0)},
        "user_scheme_serial": 0,
        "locked": False,
        "roles": [],
        "password": "$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C",
        "serial": 1,
        "last_pw_change": 1265013000,
        "enforce_pw_change": True,
        "num_failed_logins": 0,
    }


@managedtest
def test_openapi_user_edit_auth(aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch):
    monkeypatch.setattr(
        "cmk.gui.watolib.global_settings.rulebased_notifications_enabled", lambda: True
    )

    name = "foo"
    alias = "Foo Bar"

    user_detail = {
        "username": name,
        "fullname": alias,
        "customer": "provider",
        "roles": ["user"],
        "auth_option": {"auth_type": "password", "password": "password"},
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
    assert extensions["enforce_password_change"] is False

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


@managedtest
def test_openapi_user_internal_auth_handling(monkeypatch, run_as_superuser):
    monkeypatch.setattr(
        "cmk.gui.watolib.global_settings.rulebased_notifications_enabled", lambda: True
    )
    monkeypatch.setattr(
        "cmk.gui.plugins.userdb.htpasswd.hash_password",
        lambda x: "$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C",
    )

    name = UserId("foo")

    user_data = {
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
                "password": "$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C",
                "last_pw_change": 1265011200,
                "serial": 1,
                "disable_notifications": {},
            },
            "is_new_user": True,
        }
    }

    with run_as_superuser():
        edit_users(user_data)

    assert _load_internal_attributes(name) == {
        "alias": "Foo Bar",
        "customer": "provider",
        "email": "",
        "pager": "",
        "contactgroups": [],
        "fallback_contact": False,
        "disable_notifications": {},
        "user_scheme_serial": 0,
        "locked": False,
        "roles": ["user"],
        "password": "$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C",
        "serial": 1,
        "last_pw_change": 1265011200,
        "enforce_pw_change": True,
        "num_failed_logins": 0,
    }

    with freeze_time("2010-02-01 08:30:00"):
        updated_internal_attributes = _api_to_internal_format(
            _load_user(name),
            {"auth_option": {"secret": "QWXWBFUCSUOXNCPJUMS@", "auth_type": "automation"}},
        )
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
        "user_scheme_serial": 0,
        "locked": False,
        "roles": ["user"],
        "automation_secret": "QWXWBFUCSUOXNCPJUMS@",
        "password": "$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C",
        "serial": 1,  # this is 2 internally but the function is not invoked here
        "last_pw_change": 1265011200,
        "enforce_pw_change": True,
        "num_failed_logins": 0,
    }

    with freeze_time("2010-02-01 09:00:00"):
        updated_internal_attributes = _api_to_internal_format(
            _load_user(name), {"auth_option": {"auth_type": "remove"}}
        )
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
        "user_scheme_serial": 0,
        "locked": False,
        "roles": ["user"],
        "serial": 1,
        "last_pw_change": 1265011200,  # no change in time from previous edit
        "enforce_pw_change": True,
        "num_failed_logins": 0,
    }


@managedtest
def test_openapi_managed_global_edition(aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch):
    monkeypatch.setattr(
        "cmk.gui.watolib.global_settings.rulebased_notifications_enabled", lambda: True
    )
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
def test_managed_global_internal(monkeypatch, run_as_superuser):
    # this test uses the internal mechanics of the user endpoint
    monkeypatch.setattr(
        "cmk.gui.watolib.global_settings.rulebased_notifications_enabled", lambda: True
    )

    user_data = {
        "user": {
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
        edit_users(user_data)
    user_internal = _load_user(UserId("user"))
    user_endpoint_attrs = complement_customer(_internal_to_api_format(user_internal))
    assert user_endpoint_attrs["customer"] == "global"


@managedtest
def test_global_full_configuration(aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch):
    # this test uses the internal mechanics of the user endpoint
    monkeypatch.setattr(
        "cmk.gui.watolib.global_settings.rulebased_notifications_enabled", lambda: True
    )

    user_detail = {
        "username": "cmkuser",
        "fullname": "Mathias Kettner",
        "customer": "global",
        "auth_option": {"auth_type": "password", "password": "password"},
        "disable_login": False,
        "contact_options": {"email": "user@example.com"},
        "pager_address": "",
        "idle_timeout": {"option": "global"},
        "roles": ["user"],
        "disable_notifications": {"disable": False},
        "language": "en",
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
        "enforce_password_change": False,
        "interface_options": {
            "interface_theme": "default",
            "mega_menu_icons": "topic",
            "navigation_bar_icons": "hide",
            "show_mode": "default",
            "sidebar_position": "right",
        },
    }


def test_managed_idle_internal(with_automation_user, monkeypatch, run_as_superuser):
    # this test uses the internal mechanics of the user endpoint
    monkeypatch.setattr(
        "cmk.gui.watolib.global_settings.rulebased_notifications_enabled", lambda: True
    )
    username, _secret = with_automation_user

    user_data = {
        "user": {
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
        edit_users(user_data)

    user_internal = _load_user(UserId("user"))
    user_endpoint_attrs = complement_customer(_internal_to_api_format(user_internal))
    assert "idle_timeout" not in _load_user(username)
    assert user_endpoint_attrs["idle_timeout"] == {"option": "global"}


@managedtest
def test_openapi_user_update_contact_options(
    aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch: MonkeyPatch
) -> None:
    # this test uses the internal mechanics of the user endpoint
    monkeypatch.setattr(
        "cmk.gui.watolib.global_settings.rulebased_notifications_enabled", lambda: True
    )

    user_detail = {
        "username": "cmkuser",
        "fullname": "Mathias Kettner",
        "customer": "global",
        "auth_option": {"auth_type": "password", "password": "password"},
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
        "enforce_password_change": False,
        "interface_options": {
            "interface_theme": "default",
            "mega_menu_icons": "topic",
            "navigation_bar_icons": "hide",
            "show_mode": "default",
            "sidebar_position": "right",
        },
    }


@managedtest
def test_openapi_user_disable_notifications(aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch):
    # this test uses the internal mechanics of the user endpoint
    monkeypatch.setattr(
        "cmk.gui.watolib.global_settings.rulebased_notifications_enabled", lambda: True
    )

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
def test_show_all_users_with_no_email(aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch):
    """Test a user which has no email internally similar to the internal cmkadmin user"""
    monkeypatch.setattr(
        "cmk.gui.watolib.global_settings.rulebased_notifications_enabled", lambda: True
    )
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
        "cmk.gui.userdb.load_contacts",
        lambda: {},
    )
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/user_config/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert len(resp.json["value"]) == 2
    assert all(("contact_options" not in user["extensions"] for user in resp.json["value"]))


@managedtest
def test_user_enforce_password_change_option(aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch):
    """Test enforce password change option for create and update endpoints"""
    monkeypatch.setattr(
        "cmk.gui.watolib.global_settings.rulebased_notifications_enabled", lambda: True
    )

    user_detail = {
        "username": "cmkuser",
        "fullname": "Mathias Kettner",
        "customer": "global",
        "auth_option": {
            "auth_type": "password",
            "password": "password",
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
    assert resp.json["extensions"]["enforce_password_change"] is True

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
    assert update_resp.json_body["extensions"]["enforce_password_change"] is False


@managedtest
def test_user_interface_settings(aut_user_auth_wsgi_app: WebTestAppForCMK, monkeypatch):
    """Test enforce password change option for create and update endpoints"""
    monkeypatch.setattr(
        "cmk.gui.watolib.global_settings.rulebased_notifications_enabled", lambda: True
    )
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


def _random_string(size):
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(size))


def _load_internal_attributes(username):
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
