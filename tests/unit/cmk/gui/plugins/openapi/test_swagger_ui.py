#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def test_swagger_ui_http(wsgi_app) -> None:
    resp = wsgi_app.get("/NO_SITE/check_mk/api/1.0.0/ui/index.html", status=200)
    assert resp.headers["content-type"] == "text/html"
    assert b"//" in resp.body
    assert b"petstore" not in resp.body
    assert b"check_mk/api" in resp.body
    assert b"openapi-swagger-ui.yaml" in resp.body


def test_swagger_ui_https(wsgi_app) -> None:
    wsgi_app.extra_environ = {"wsgi.url_scheme": "https"}
    resp = wsgi_app.get("/NO_SITE/check_mk/api/1.0.0/ui/index.html", status=200)
    assert b"//" in resp.body
    assert b"petstore" not in resp.body
    assert b"check_mk/api" in resp.body
    assert b"openapi-swagger-ui.yaml" in resp.body


def test_swagger_ui_resource_urls(wsgi_app) -> None:
    resp = wsgi_app.get("/NO_SITE/check_mk/api/0/ui/swagger-ui.js", status=200)
    assert resp.headers["content-type"] in ("application/javascript", "text/javascript")
    resp = wsgi_app.get("/NO_SITE/check_mk/api/0/ui/swagger-ui.css", status=200)
    assert resp.headers["content-type"] == "text/css"
    resp = wsgi_app.get("/NO_SITE/check_mk/api/0/ui/swagger-ui.css.map", status=200)
    assert resp.headers["content-type"] == "text/plain; charset=utf-8"
