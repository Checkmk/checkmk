# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils import version

managedtest = pytest.mark.skipif(not version.is_managed_edition(), reason="see #7213")


@managedtest
@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_password(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/password/collections/all",
        params=json.dumps(
            {
                "ident": "foo",
                "title": "foobar",
                "owner": "admin",
                "password": "tt",
                "shared": ["all"],
                "customer": "global",
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/password/fooz",
        params=json.dumps({"title": "foobu", "comment": "Something but nothing random"}),
        status=404,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/password/foo",
        params=json.dumps({"title": "foobu", "comment": "Something but nothing random"}),
        status=200,
        headers={"Accept": "application/json", "If-Match": resp.headers["ETag"]},
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/password/foo",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert resp.json["extensions"] == {
        "comment": "Something but nothing random",
        "documentation_url": "",
        "owned_by": None,
        "shared": ["all"],
        "customer": "global",
    }


@managedtest
@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_password_admin(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/password/collections/all",
        params=json.dumps(
            {
                "ident": "test",
                "title": "Checkmk",
                "owner": "admin",
                "password": "tt",
                "shared": [],
                "customer": "provider",
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/password/test",
        headers={"Accept": "application/json"},
        status=200,
    )


@managedtest
@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_password_customer(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/password/collections/all",
        params=json.dumps(
            {
                "ident": "test",
                "title": "Checkmk",
                "owner": "admin",
                "password": "tt",
                "shared": [],
                "customer": "provider",
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )
    assert resp.json_body["extensions"]["customer"] == "provider"

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/password/test",
        params=json.dumps(
            {
                "customer": "global",
            }
        ),
        headers={"Accept": "application/json"},
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/password/test",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert resp.json_body["extensions"]["customer"] == "global"


@managedtest
@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_password_delete(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/password/collections/all",
        params=json.dumps(
            {
                "ident": "foo",
                "title": "foobar",
                "owner": "admin",
                "password": "tt",
                "shared": ["all"],
                "customer": "global",
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/password/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert len(resp.json_body["value"]) == 1

    _resp = aut_user_auth_wsgi_app.call_method(
        "delete",
        base + "/objects/password/nothing",
        headers={"Accept": "application/json"},
        status=404,
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "delete",
        base + "/objects/password/foo",
        headers={"Accept": "application/json"},
        status=204,
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "get", base + "/objects/password/foo", headers={"Accept": "application/json"}, status=404
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/password/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert len(resp.json_body["value"]) == 0
