#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import urllib.parse
from collections.abc import Mapping
from typing import Optional, Tuple

import pytest

from tests.testlib.rest_api_client import RequestHandler, Response, RestApiClient

from tests.unit.cmk.gui.conftest import HTTPMethod, WebTestAppForCMK


@pytest.fixture(name="aut_user_auth_wsgi_app")
def fixture_aut_user_auth_wsgi_app(
    wsgi_app: WebTestAppForCMK,
    with_automation_user: Tuple[str, str],
) -> WebTestAppForCMK:
    wsgi_app.set_authorization(("Bearer", " ".join(with_automation_user)))
    return wsgi_app


@pytest.fixture(name="base")
def fixture_base() -> str:
    return "/NO_SITE/check_mk/api/1.0"


class WebTestAppRequestHandler(RequestHandler):
    def __init__(self, wsgi_app: WebTestAppForCMK):
        self.app = wsgi_app

    def set_credentials(self, username: str, password: str) -> None:
        self.app.set_authorization(("Bearer", f"{username} {password}"))

    def request(
        self,
        method: HTTPMethod,
        url: str,
        query_params: Optional[Mapping[str, str]] = None,
        body: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Response:
        if query_params is not None:
            query_string = "?" + urllib.parse.urlencode(query_params)
        else:
            query_string = ""
        resp = self.app.call_method(
            method,
            url + query_string,
            params=body,
            headers=dict(headers or {}),
            expect_errors=True,
        )
        return Response(status_code=resp.status_code, body=resp.body, headers=resp.headers)


@pytest.fixture()
def api_client(aut_user_auth_wsgi_app: WebTestAppForCMK, base: str) -> RestApiClient:
    return RestApiClient(WebTestAppRequestHandler(aut_user_auth_wsgi_app), base)
