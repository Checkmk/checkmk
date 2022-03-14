#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.unit.cmk.gui.conftest import WebTestAppForCMK


def test_openapi_accept_header_missing(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        status=406,
    )
    assert resp.json == {
        "detail": "Please specify an Accept Header.",
        "status": 406,
        "title": "Not Acceptable",
    }


def test_openapi_accept_header_matches(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        {},  # params
        {"Accept": "application/json"},  # headers
        status=200,
    )
    assert resp.json["value"] == []


def test_openapi_accept_header_invalid(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
        {},  # params
        {"Accept": "asd-asd-asd"},  # headers
        status=406,
    )
    assert resp.json == {
        "detail": "Can not send a response with the content type specified in the "
        "'Accept' Header. Accept Header: asd-asd-asd. Supported content "
        "types: [application/json]",
        "status": 406,
        "title": "Not Acceptable",
    }
