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

from cmk.gui.plugins.openapi.endpoints.user_config import _internal_to_api_format, _load_user, _api_to_internal_format
from cmk.gui.plugins.openapi.endpoints.utils import complement_customer
from cmk.gui.watolib.users import edit_users
from cmk.utils import version

managedtest = pytest.mark.skipif(not version.is_managed_edition(), reason="see #7213")


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
    assert resp.json_body['extensions'] == {
        'fullname': 'User Name',
        'customer': 'global',
        'contactgroups': [],
        'disable_notifications': {},
        'contact_options': {
            "email": '',
            "fallback_contact": False
        },
        'idle_timeout': {
            'option': 'global'
        },
        'disable_login': False,
        'pager_address': '',
        'roles': [],
    }

    resp = wsgi_app.call_method(
        'put',
        base + "/objects/user_config/user",
        params=json.dumps({"customer": "provider"}),
        status=200,
        content_type='application/json',
    )
    assert resp.json_body['extensions']['customer'] == 'provider'


@managedtest
def test_openapi_user_minimal_settings(wsgi_app, with_automation_user, monkeypatch):
    monkeypatch.setattr("cmk.gui.watolib.global_settings.rulebased_notifications_enabled",
                        lambda: True)
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    edit_users({
        "user": {
            "attributes": {
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
                'email': '',
                'fallback_contact': False,
                'disable_notifications': {},
            },
            "is_new_user": True,
        }
    })

    user_attributes = _load_internal_attributes("user")

    assert user_attributes == {
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
    assert resp.json_body['extensions'] == {
        'fullname': 'User Name',
        'customer': 'provider',
        'pager_address': '',
        'contactgroups': [],
        'idle_timeout': {
            'option': 'global'
        },
        'contact_options': {
            'email': '',
            'fallback_contact': False,
        },
        'disable_notifications': {},
        'disable_login': False,
        'roles': [],
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
    assert resp.json_body['extensions'] == {
        'fullname': 'User Name',
        'customer': 'provider',
        'contact_options': {
            'email': '',
            'fallback_contact': False,
        },
        'idle_timeout': {
            'option': 'disable',
        },
        'pager_address': '',
        'disable_login': False,
        'contactgroups': [],
        'disable_notifications': {},
        'roles': ['user'],
    }


@managedtest
def test_openapi_all_users(wsgi_app, with_automation_user):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + ' ' + secret))
    base = '/NO_SITE/check_mk/api/1.0'

    resp = wsgi_app.call_method('get',
                                base + '/domain-types/user_config/collections/all',
                                status=200)
    users = resp.json_body['value']
    assert len(users) == 1

    _user_resp = wsgi_app.call_method('get', users[0]['links'][0]['href'], status=200)


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

    assert resp.json_body['extensions'] == {
        'contact_options': {
            'email': '',
            'fallback_contact': False
        },
        'disable_login': False,
        'fullname': 'KPECYCq79E',
        'pager_address': '',
        'contactgroups': [],
        'customer': 'provider',
        'disable_notifications': {
            'timerange': {
                'end_time': '2020-01-02T00:00:00+00:00',
                'start_time': '2020-01-01T00:00:00+00:00'
            }
        },
        'idle_timeout': {
            'option': 'global'
        },
        'roles': []
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
def test_openapi_user_internal_with_notifications(wsgi_app, with_automation_user, monkeypatch):
    monkeypatch.setattr("cmk.gui.watolib.global_settings.rulebased_notifications_enabled",
                        lambda: True)
    monkeypatch.setattr(
        "cmk.gui.plugins.userdb.htpasswd.hash_password",
        lambda x: '$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C')
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    name = _random_string(10)

    edit_users({
        name: {
            "attributes": {
                'ui_theme': None,
                'ui_sidebar_position': None,
                'nav_hide_icons_title': None,
                'icons_per_item': None,
                'show_mode': None,
                'start_url': None,
                'force_authuser': False,
                'enforce_pw_change': True,
                'alias': 'KPECYCq79E',
                'locked': False,
                'pager': '',
                'roles': [],
                'contactgroups': [],
                'email': '',
                'fallback_contact': False,
                'password': '$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C',
                'last_pw_change': 1265013000,
                'serial': 1,
                'disable_notifications': {
                    'timerange': (1577836800.0, 1577923200.0)
                }
            },
            "is_new_user": True,
        }
    })

    assert _load_internal_attributes(name) == {
        'alias': 'KPECYCq79E',
        'customer': 'provider',
        'pager': '',
        'contactgroups': [],
        'email': '',
        'fallback_contact': False,
        'disable_notifications': {
            'timerange': (1577836800.0, 1577923200.0)
        },
        'user_scheme_serial': 0,
        'locked': False,
        'roles': [],
        'password': '$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C',
        'serial': 1,
        'last_pw_change': 1265013000,
        'enforce_pw_change': True
    }


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
    assert resp.json_body['extensions'] == {
        'contact_options': {
            'email': '',
            'fallback_contact': False
        },
        'disable_login': False,
        'fullname': 'Foo Bar',
        'pager_address': '',
        'customer': 'provider',
        'contactgroups': [],
        'disable_notifications': {},
        'idle_timeout': {
            'option': 'global'
        },
        'roles': ['user'],
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
    assert resp.json_body['extensions'] == {
        'contact_options': {
            'email': '',
            'fallback_contact': False
        },
        'disable_login': False,
        'fullname': 'Foo Bar',
        'pager_address': '',
        'customer': 'provider',
        'contactgroups': [],
        'disable_notifications': {},
        'idle_timeout': {
            'option': 'global'
        },
        'roles': ['user'],
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
    assert resp.json_body['extensions'] == {
        'contact_options': {
            'email': '',
            'fallback_contact': False
        },
        'disable_login': False,
        'fullname': 'Foo Bar',
        'pager_address': '',
        'customer': 'provider',
        'contactgroups': [],
        'disable_notifications': {},
        'idle_timeout': {
            'option': 'global'
        },
        'roles': ['user'],
    }


@managedtest
def test_openapi_user_internal_auth_handling(wsgi_app, with_automation_user, monkeypatch):
    monkeypatch.setattr("cmk.gui.watolib.global_settings.rulebased_notifications_enabled",
                        lambda: True)
    monkeypatch.setattr(
        "cmk.gui.plugins.userdb.htpasswd.hash_password",
        lambda x: '$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C')
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    name = "foo"

    edit_users({
        name: {
            "attributes": {
                'ui_theme': None,
                'ui_sidebar_position': None,
                'nav_hide_icons_title': None,
                'icons_per_item': None,
                'show_mode': None,
                'start_url': None,
                'force_authuser': False,
                'enforce_pw_change': True,
                'alias': 'Foo Bar',
                'locked': False,
                'pager': '',
                'roles': ['user'],
                'contactgroups': [],
                'email': '',
                'fallback_contact': False,
                'password': '$5$rounds=535000$eUtToQgKz6n7Qyqk$hh5tq.snoP4J95gVoswOep4LbUxycNG1QF1HI7B4d8C',
                'last_pw_change': 1265011200,
                'serial': 1,
                'disable_notifications': {}
            },
            "is_new_user": True
        }
    })
    assert _load_internal_attributes(name) == {
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

    with freeze_time("2010-02-01 08:30:00"):
        updated_internal_attributes = _api_to_internal_format(
            _load_user(name),
            {'auth_option': {
                'secret': 'QWXWBFUCSUOXNCPJUMS@',
                'auth_type': 'automation'
            }})
        edit_users({name: {
            "attributes": updated_internal_attributes,
            "is_new_user": False,
        }})

    assert _load_internal_attributes(name) == {
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
        'serial': 1,  # this is 2 internally but the function is not invoked here
        'last_pw_change': 1265011200,
        'enforce_pw_change': True
    }

    with freeze_time("2010-02-01 09:00:00"):
        updated_internal_attributes = _api_to_internal_format(
            _load_user(name), {'auth_option': {
                'auth_type': 'remove'
            }})
        edit_users({name: {
            "attributes": updated_internal_attributes,
            "is_new_user": False,
        }})
    assert _load_internal_attributes(name) == {
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
        'serial': 1,
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
    assert resp.json_body['extensions'] == {
        'contact_options': {
            'email': '',
            'fallback_contact': False
        },
        'disable_login': False,
        'fullname': 'User Name',
        'pager_address': '',
        'customer': 'global',
        'contactgroups': [],
        'disable_notifications': {},
        'idle_timeout': {
            'option': 'global'
        },
        'roles': [],
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
    user_internal = _load_user("user")
    user_endpoint_attrs = complement_customer(_internal_to_api_format(user_internal))
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

    resp = wsgi_app.call_method('get', base + "/objects/user_config/cmkuser", status=200)

    assert resp.json_body['extensions'] == {
        'contact_options': {
            'email': 'user@example.com',
            'fallback_contact': False
        },
        'disable_login': False,
        'fullname': 'Mathias Kettner',
        'pager_address': '',
        'roles': ['user'],
        'contactgroups': [],
        'language': 'en',
        'customer': 'global',
        'idle_timeout': {
            'option': 'global'
        },
        'disable_notifications': {},
    }


@managedtest
def test_managed_idle_internal(wsgi_app, with_automation_user, monkeypatch):
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
    user_internal = _load_user("user")
    user_endpoint_attrs = complement_customer(_internal_to_api_format(user_internal))
    assert "idle_timeout" not in _load_user(username)
    assert user_endpoint_attrs["idle_timeout"] == {"option": "global"}


@managedtest
def test_openapi_user_update_contact_options(wsgi_app, with_automation_user, monkeypatch):
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
        resp = wsgi_app.call_method(
            'post',
            base + "/domain-types/user_config/collections/all",
            params=json.dumps(user_detail),
            status=200,
            content_type='application/json',
        )

    _ = wsgi_app.call_method(
        'put',
        base + "/objects/user_config/cmkuser",
        params=json.dumps({"contact_options": {
            "fallback_contact": True
        }}),
        status=400,
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )

    resp = wsgi_app.call_method('get', base + '/objects/user_config/cmkuser', status=200)
    assert resp.json_body['extensions'] == {
        'contact_options': {
            'email': '',
            'fallback_contact': False
        },
        'disable_login': False,
        'fullname': 'Mathias Kettner',
        'idle_timeout': {
            'option': 'global'
        },
        'pager_address': '',
        'roles': ['user'],
        'contactgroups': [],
        'language': 'en',
        'customer': 'global',
        'disable_notifications': {},
    }


@managedtest
def test_openapi_user_disable_notifications(wsgi_app, with_automation_user, monkeypatch):
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
        'disable_notifications': {
            'disable': True
        },
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
    resp = wsgi_app.call_method('get', base + "/objects/user_config/cmkuser", status=200)
    assert resp.json_body["extensions"] == {
        'contact_options': {
            'email': '',
            'fallback_contact': False
        },
        'disable_login': False,
        'fullname': 'Mathias Kettner',
        'idle_timeout': {
            'option': 'global'
        },
        'pager_address': '',
        'roles': [],
        'contactgroups': [],
        'customer': 'global',
        'disable_notifications': {
            "disable": True,
        },
    }

    resp = wsgi_app.call_method(
        'put',
        base + "/objects/user_config/cmkuser",
        params=json.dumps({"disable_notifications": {
            "disable": False
        }}),
        status=200,
        headers={'If-Match': resp.headers['ETag']},
        content_type='application/json',
    )
    assert resp.json_body["extensions"] == {
        'contact_options': {
            'email': '',
            'fallback_contact': False
        },
        'disable_login': False,
        'fullname': 'Mathias Kettner',
        'idle_timeout': {
            'option': 'global'
        },
        'pager_address': '',
        'roles': [],
        'contactgroups': [],
        'customer': 'global',
        'disable_notifications': {},
    }


@managedtest
def test_show_all_users_with_no_email(wsgi_app, with_automation_user, monkeypatch):
    """Test a user which has no email internally similar to the internal cmkadmin user"""
    monkeypatch.setattr("cmk.gui.watolib.global_settings.rulebased_notifications_enabled",
                        lambda: True)

    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))
    user_detail = {
        "username": "internal_user",
        "fullname": "Internal",
        "customer": "global",
    }

    base = "/NO_SITE/check_mk/api/1.0"
    _resp = wsgi_app.call_method(
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
    resp = wsgi_app.call_method(
        "get",
        base + "/domain-types/user_config/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert len(resp.json["value"]) == 2
    assert all(("contact_options" not in user["extensions"] for user in resp.json["value"]))


def _random_string(size):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(size))


def _load_internal_attributes(username):
    return complement_customer(_internal_attributes(_load_user(username)))


def _internal_attributes(user_attributes):
    return {
        k: v for k, v in user_attributes.items() if k not in (
            "nav_hide_icons_title",
            "icons_per_item",
            "show_mode",
            "ui_theme",
            "ui_sidebar_position",
            "start_url",
            "force_authuser",
        )
    }
