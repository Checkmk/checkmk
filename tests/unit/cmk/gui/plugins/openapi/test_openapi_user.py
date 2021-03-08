#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import random
import string
from freezegun import freeze_time

from cmk.gui.plugins.openapi.endpoints.user_config import user_config_attributes
from cmk.gui.plugins.openapi.endpoints.utils import complement_customer
from cmk.gui.watolib.users import edit_users
from tests.unit.cmk.gui.plugins.openapi.test_version import managedtest  # type: ignore[import]


@managedtest
def test_openapi_customer(wsgi_app, with_automation_user, monkeypatch):
    monkeypatch.setattr("cmk.gui.watolib.global_settings.rulebased_notifications_enabled",
                        lambda: True)
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    user_detail = {
        'username': 'user',
        'fullname': 'User Name',
        'customer': 'global',
    }

    base = "/NO_SITE/check_mk/api/1.0"
    with freeze_time("2010-02-01 08:00:00"):
        resp = wsgi_app.call_method(
            'post',
            base + "/domain-types/user_config/collections/all",
            params=json.dumps(user_detail),
            status=200,
            content_type='application/json',
        )
    assert resp.json_body["extensions"]["attributes"] == {
        'alias': 'User Name',
        'customer': 'global',
        'contactgroups': [],
        'disable_notifications': {},
        'email': '',
        'enforce_pw_change': False,
        'fallback_contact': False,
        'locked': False,
        'pager': '',
        'roles': [],
        'user_scheme_serial': 0
    }

    resp = wsgi_app.call_method(
        'put',
        base + "/objects/user_config/user",
        params=json.dumps({"customer": "provider"}),
        status=200,
        content_type='application/json',
    )
    assert resp.json_body["extensions"]["attributes"]["customer"] == "provider"


@managedtest
def test_openapi_user_minimal_settings(wsgi_app, with_automation_user, monkeypatch):
    monkeypatch.setattr("cmk.gui.watolib.global_settings.rulebased_notifications_enabled",
                        lambda: True)
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    user_detail = {'username': 'user', 'fullname': 'User Name', 'customer': 'provider'}

    base = "/NO_SITE/check_mk/api/1.0"
    with freeze_time("2010-02-01 08:00:00"):
        resp = wsgi_app.call_method(
            'post',
            base + "/domain-types/user_config/collections/all",
            params=json.dumps(user_detail),
            status=200,
            content_type='application/json',
        )
    assert resp.json_body["extensions"]["attributes"] == {
        'alias': 'User Name',
        'customer': 'provider',
        'contactgroups': [],
        'disable_notifications': {},
        'email': '',
        'enforce_pw_change': False,
        'fallback_contact': False,
        'locked': False,
        'pager': '',
        'roles': [],
        'user_scheme_serial': 0
    }


@managedtest
def test_openapi_user_minimal_password_settings(wsgi_app, with_automation_user, monkeypatch):
    monkeypatch.setattr("cmk.gui.watolib.global_settings.rulebased_notifications_enabled",
                        lambda: True)
    monkeypatch.setattr(
        "cmk.gui.plugins.userdb.htpasswd.hash_password",
        lambda x: '$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C')
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    user_detail = {
        'username': 'user',
        'fullname': 'User Name',
        'customer': 'provider',
        'auth_option': {
            "auth_type": 'password',
            'password': 'password',
        }
    }

    base = "/NO_SITE/check_mk/api/1.0"
    with freeze_time("2010-02-01 08:00:00"):
        resp = wsgi_app.call_method(
            'post',
            base + "/domain-types/user_config/collections/all",
            params=json.dumps(user_detail),
            status=200,
            content_type='application/json',
        )
    assert resp.json_body["extensions"]["attributes"] == {
        'alias': 'User Name',
        'customer': 'provider',
        'email': '',
        'pager': '',
        'contactgroups': [],
        'fallback_contact': False,
        'disable_notifications': {},
        'user_scheme_serial': 0,
        'locked': False,
        'roles': [],
        'password': '$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C',
        'serial': 1,
        'last_pw_change': 1265011200,
        'enforce_pw_change': True
    }

    edit_details = {
        'auth_option': {
            'auth_type': 'automation',
            'secret': 'SOMEAUTOMATION',
        },
        'roles': ['user'],
        'idle_timeout': {
            'option': 'disable'
        }
    }
    with freeze_time("2010-02-01 08:30:00"):
        resp = wsgi_app.call_method(
            'put',
            base + "/objects/user_config/user",
            params=json.dumps(edit_details),
            status=200,
            headers={'If-Match': resp.headers['ETag']},
            content_type='application/json',
        )
    assert resp.json_body["extensions"]["attributes"] == {
        'alias': 'User Name',
        'customer': 'provider',
        'email': '',
        'pager': '',
        'contactgroups': [],
        'fallback_contact': False,
        'disable_notifications': {},
        'user_scheme_serial': 0,
        'locked': False,
        'roles': ['user'],
        'password': '$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C',
        'serial': 2,
        'num_failed_logins': 0,
        'last_pw_change': 1265011200,
        'enforce_pw_change': True,
        'automation_secret': 'SOMEAUTOMATION',
        'idle_timeout': False,
    }


@managedtest
def test_openapi_user_config(wsgi_app, with_automation_user, monkeypatch):
    monkeypatch.setattr("cmk.gui.watolib.global_settings.rulebased_notifications_enabled",
                        lambda: True)
    monkeypatch.setattr(
        "cmk.gui.plugins.userdb.htpasswd.hash_password",
        lambda x: '$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C')
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    name = _random_string(10)
    alias = "KPECYCq79E"

    user_detail = {
        'username': name,
        'fullname': alias,
        'customer': 'provider',
        'auth_option': {
            "auth_type": "password",
            "password": "hello"
        },
        'disable_notifications': {
            "timerange": {
                'start_time': '2020-01-01T00:00:00Z',
                'end_time': '2020-01-02T00:00:00Z'
            }
        }
    }

    base = "/NO_SITE/check_mk/api/1.0"
    with freeze_time("2010-02-01 08:30:00"):
        _resp = wsgi_app.call_method(
            'post',
            base + "/domain-types/user_config/collections/all",
            params=json.dumps(user_detail),
            status=200,
            content_type='application/json',
        )

    resp = wsgi_app.call_method('get', base + f"/objects/user_config/{name}", status=200)

    assert resp.json_body["extensions"]["attributes"] == {
        'alias': 'KPECYCq79E',
        'customer': 'provider',
        'pager': '',
        'contactgroups': [],
        'email': '',
        'fallback_contact': False,
        'disable_notifications': {
            'timerange': [1577836800.0, 1577923200.0]
        },
        'user_scheme_serial': 0,
        'locked': False,
        'roles': [],
        'password': '$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C',
        'serial': 1,
        'num_failed_logins': 0,
        'last_pw_change': 1265013000,
        'enforce_pw_change': True
    }

    collection_resp = wsgi_app.call_method(
        'get',
        base + "/domain-types/user_config/collections/all",
        status=200,
    )
    assert len(collection_resp.json_body["value"]) == 2

    _resp = wsgi_app.call_method(
        'delete',
        base + f"/objects/user_config/{name}",
        status=204,
        headers={'If-Match': resp.headers['Etag']},
    )

    _resp = wsgi_app.call_method('get', base + f"/objects/user_config/{name}", status=404)

    resp = wsgi_app.call_method(
        'get',
        base + "/domain-types/user_config/collections/all",
        status=200,
    )
    assert len(resp.json_body["value"]) == 1


@managedtest
def test_openapi_user_edit_auth(wsgi_app, with_automation_user, monkeypatch):
    monkeypatch.setattr("cmk.gui.watolib.global_settings.rulebased_notifications_enabled",
                        lambda: True)
    monkeypatch.setattr(
        "cmk.gui.plugins.userdb.htpasswd.hash_password",
        lambda x: '$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C')
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    name = "foo"
    alias = "Foo Bar"

    user_detail = {
        'username': name,
        'fullname': alias,
        'customer': 'provider',
        'roles': ["user"],
        "auth_option": {
            "auth_type": "password",
            "password": "password"
        },
    }

    base = "/NO_SITE/check_mk/api/1.0"
    with freeze_time("2010-02-01 08:00:00"):
        resp = wsgi_app.call_method(
            'post',
            base + "/domain-types/user_config/collections/all",
            params=json.dumps(user_detail),
            status=200,
            content_type='application/json',
        )
    assert resp.json_body["extensions"]["attributes"] == {
        'alias': 'Foo Bar',
        'customer': 'provider',
        'email': '',
        'pager': '',
        'contactgroups': [],
        'fallback_contact': False,
        'disable_notifications': {},
        'user_scheme_serial': 0,
        'locked': False,
        'roles': ['user'],
        'password': '$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C',
        'serial': 1,
        'last_pw_change': 1265011200,
        'enforce_pw_change': True,
    }

    edit_details = {
        "auth_option": {
            "auth_type": "automation",
            "secret": "QWXWBFUCSUOXNCPJUMS@"
        },
    }

    with freeze_time("2010-02-01 08:30:00"):
        resp = wsgi_app.call_method(
            'put',
            base + "/objects/user_config/foo",
            params=json.dumps(edit_details),
            status=200,
            headers={'If-Match': resp.headers['ETag']},
            content_type='application/json',
        )
    assert resp.json_body["extensions"]["attributes"] == {
        'alias': 'Foo Bar',
        'customer': 'provider',
        'email': '',
        'pager': '',
        'contactgroups': [],
        'fallback_contact': False,
        'disable_notifications': {},
        'user_scheme_serial': 0,
        'locked': False,
        'roles': ['user'],
        'automation_secret': 'QWXWBFUCSUOXNCPJUMS@',
        'password': '$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C',
        'serial': 2,
        'num_failed_logins': 0,
        'last_pw_change': 1265011200,
        'enforce_pw_change': True
    }

    remove_details = {
        "auth_option": {
            "auth_type": "remove",
        },
    }
    with freeze_time("2010-02-01 09:00:00"):
        resp = wsgi_app.call_method(
            'put',
            base + "/objects/user_config/foo",
            params=json.dumps(remove_details),
            status=200,
            headers={'If-Match': resp.headers['ETag']},
            content_type='application/json',
        )
    assert resp.json_body["extensions"]["attributes"] == {
        'alias': 'Foo Bar',
        'customer': 'provider',
        'email': '',
        'pager': '',
        'contactgroups': [],
        'fallback_contact': False,
        'disable_notifications': {},
        'user_scheme_serial': 0,
        'locked': False,
        'roles': ['user'],
        'serial': 2,
        'num_failed_logins': 0,
        'last_pw_change': 1265011200,  # no change in time from previous edit
        'enforce_pw_change': True
    }


@managedtest
def test_openapi_managed_global_edition(wsgi_app, with_automation_user, monkeypatch):
    monkeypatch.setattr("cmk.gui.watolib.global_settings.rulebased_notifications_enabled",
                        lambda: True)
    monkeypatch.setattr("cmk.utils.version.is_managed_edition", lambda: True)
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    user_detail = {
        'username': 'user',
        'fullname': 'User Name',
        'customer': 'global',
    }

    base = "/NO_SITE/check_mk/api/1.0"
    with freeze_time("2010-02-01 08:00:00"):
        resp = wsgi_app.call_method(
            'post',
            base + "/domain-types/user_config/collections/all",
            params=json.dumps(user_detail),
            status=200,
            content_type='application/json',
        )
    assert resp.json_body["extensions"]["attributes"] == {
        'alias': 'User Name',
        'customer': 'global',
        'contactgroups': [],
        'disable_notifications': {},
        'email': '',
        'enforce_pw_change': False,
        'fallback_contact': False,
        'locked': False,
        'pager': '',
        'roles': [],
        'user_scheme_serial': 0
    }


@managedtest
def test_managed_global_internal(wsgi_app, with_automation_user, monkeypatch):
    # this test uses the internal mechanics of the user endpoint
    monkeypatch.setattr("cmk.gui.watolib.global_settings.rulebased_notifications_enabled",
                        lambda: True)
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    edit_users({
        'user': {
            'attributes': {
                'ui_theme': None,
                'ui_sidebar_position': None,
                'nav_hide_icons_title': None,
                'icons_per_item': None,
                'show_mode': None,
                'start_url': None,
                'force_authuser': False,
                'enforce_pw_change': False,
                'alias': 'User Name',
                'locked': False,
                'pager': '',
                'roles': [],
                'contactgroups': [],
                'customer': None,  # None represents global internally
                'email': '',
                'fallback_contact': False,
                'disable_notifications': {}
            },
            'is_new_user': True
        }
    })
    user_endpoint_attrs = complement_customer(user_config_attributes("user"))
    assert user_endpoint_attrs["customer"] == "global"


@managedtest
def test_global_full_configuration(wsgi_app, with_automation_user, monkeypatch):
    # this test uses the internal mechanics of the user endpoint
    monkeypatch.setattr("cmk.gui.watolib.global_settings.rulebased_notifications_enabled",
                        lambda: True)
    monkeypatch.setattr(
        "cmk.gui.plugins.userdb.htpasswd.hash_password",
        lambda x: '$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C')

    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    user_detail = {
        'username': 'cmkuser',
        'fullname': 'Mathias Kettner',
        'customer': 'global',
        'auth_option': {
            'auth_type': 'password',
            'password': 'password'
        },
        'disable_login': False,
        'contact_options': {
            'email': 'user@example.com'
        },
        'pager_address': '',
        'idle_timeout': {
            "option": "global"
        },
        'roles': ['user'],
        'disable_notifications': {
            'disable': False
        },
        'language': 'en'
    }

    base = "/NO_SITE/check_mk/api/1.0"
    with freeze_time("2010-02-01 08:00:00"):
        _resp = wsgi_app.call_method(
            'post',
            base + "/domain-types/user_config/collections/all",
            params=json.dumps(user_detail),
            status=200,
            content_type='application/json',
        )

    resp = wsgi_app.call_method('get', base + f"/objects/user_config/cmkuser", status=200)

    assert resp.json_body["extensions"]["attributes"] == {
        'enforce_pw_change': True,
        'alias': 'Mathias Kettner',
        'locked': False,
        'pager': '',
        'num_failed_logins': 0,  # this is added afterward internally
        'roles': ['user'],
        'contactgroups': [],
        'language': 'en',
        'customer': 'global',
        'email': 'user@example.com',
        'fallback_contact': False,
        'password': '$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C',
        'last_pw_change': 1265011200,
        'serial': 1,
        'disable_notifications': {},
        'user_scheme_serial': 0,
    }


def _random_string(size):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(size))
