#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.ccc.version as cmk_version
from cmk.utils import paths

from tests.unit.cmk.web_test_app import CmkTestResponse, WebTestAppForCMK


def _get_version(app: WebTestAppForCMK, status: int = 200) -> CmkTestResponse:
    return app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/version",
        headers={
            "Accept": "application/json",
        },
        status=status,
    )


def test_headers_exposed(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    resp = _get_version(
        aut_user_auth_wsgi_app,
    )
    assert resp.headers["x-checkmk-edition"] == cmk_version.edition(paths.omd_root).short
    assert resp.headers["x-checkmk-version"] == cmk_version.__version__


def test_headers_not_exposed_for_unauthorized_users(
    wsgi_app: WebTestAppForCMK, request_context: None
) -> None:
    resp = _get_version(
        wsgi_app,
        status=401,
    )
    assert "x-checkmk-edition" not in resp.headers
    assert "x-checkmk-version" not in resp.headers
