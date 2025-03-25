#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from tests.unit.cmk.web_test_app import WebTestAppForCMK


def test_version(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/version",
        headers={"Accept": "application/json"},
        status=200,
    )

    assert set(resp.json_body.keys()) == {
        "demo",
        "edition",
        "group",
        "rest_api",
        "site",
        "versions",
    }


def test_version_404(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"
    aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/version" + base + "/version",
        headers={"Accept": "application/json"},
        status=404,
    )
