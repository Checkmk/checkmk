#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK


@pytest.fixture(scope="function", name="etags_off")
def etags_off_fixture(aut_user_auth_wsgi_app: WebTestAppForCMK):
    with aut_user_auth_wsgi_app.set_config(rest_api_etag_locking=False):
        yield


@pytest.mark.usefixtures("with_host")
def test_openapi_etag_disabled(etags_off, aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/example.com",
        headers={"Accept": "application/json"},
        status=200,
    )

    aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        headers={"Accept": "application/json"},
        status=200,
        params='{"attributes": {"ipaddress": "127.0.0.1"}}',
        content_type="application/json",
    )


@pytest.mark.usefixtures("with_host")
def test_openapi_etag_enabled(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/example.com",
        headers={"Accept": "application/json"},
        status=200,
    )

    aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        status=428,
        headers={"Accept": "application/json"},
        params='{"attributes": {"ipaddress": "127.0.0.1"}}',
        content_type="application/json",
    )
    aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        status=412,
        headers={"If-Match": "foo", "Accept": "application/json"},
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.follow_link(
        resp,
        ".../update",
        status=200,
        params='{"attributes": {"ipaddress": "127.0.0.1"}}',
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        content_type="application/json",
    )
    assert ("ipaddress", "127.0.0.1") in list(resp.json["extensions"]["attributes"].items())
