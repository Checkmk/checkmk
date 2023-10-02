#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from tests.unit.cmk.gui.conftest import WebTestAppForCMK


def test_swagger_ui_http_unauthenticated(wsgi_app: WebTestAppForCMK) -> None:
    wsgi_app.get("/NO_SITE/check_mk/api/1.0.0/ui/index.html", status=401)


def test_swagger_ui_resource_urls_unauthenticated(wsgi_app: WebTestAppForCMK) -> None:
    wsgi_app.get("/NO_SITE/check_mk/api/0/ui/swagger-ui.js", status=401)


def test_swagger_ui_http(logged_in_wsgi_app: WebTestAppForCMK) -> None:
    resp = logged_in_wsgi_app.get("/NO_SITE/check_mk/api/1.0.0/ui/index.html", status=200)
    assert resp.headers["content-type"] == "text/html; charset=utf-8"
    assert b"//" in resp.body
    assert b"petstore" not in resp.body
    assert b"openapi-swagger-ui.yaml" in resp.body


def test_swagger_ui_https(logged_in_wsgi_app: WebTestAppForCMK) -> None:
    wsgi_app = logged_in_wsgi_app
    wsgi_app.extra_environ = {"wsgi.url_scheme": "https"}
    resp = wsgi_app.get("/NO_SITE/check_mk/api/1.0.0/ui/index.html", status=200)
    assert b"//" in resp.body
    assert b"petstore" not in resp.body
    assert b"openapi-swagger-ui.yaml" in resp.body


def test_swagger_ui_resource_urls(logged_in_wsgi_app: WebTestAppForCMK) -> None:
    wsgi_app = logged_in_wsgi_app
    resp = wsgi_app.get("/NO_SITE/check_mk/api/0/ui/swagger-ui.js", status=200)
    assert resp.headers["content-type"] in (
        "application/javascript; charset=utf-8",
        "text/javascript; charset=utf-8",
    )
    resp = wsgi_app.get("/NO_SITE/check_mk/api/0/ui/swagger-ui.css", status=200)
    assert resp.headers["content-type"] == "text/css; charset=utf-8"
    resp = wsgi_app.get("/NO_SITE/check_mk/api/0/ui/swagger-ui.css.map", status=200)
    assert resp.headers["content-type"] == "application/octet-stream"
