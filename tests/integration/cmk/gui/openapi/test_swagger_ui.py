#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from tests.testlib.site import Site
from tests.testlib.web_session import CMKWebSession


@pytest.mark.skip_if_edition("saas")
def test_swagger_ui_http_unauthenticated(site: Site) -> None:
    session = CMKWebSession(site)
    session.get(f"/{site.id}/check_mk/api/v1/ui/index.html", expected_code=401)


@pytest.mark.skip_if_edition("saas")
def test_swagger_ui_resource_urls_unauthenticated(site: Site) -> None:
    session = CMKWebSession(site)
    session.get(f"/{site.id}/check_mk/api/v1/ui/swagger-ui.js", expected_code=401)


@pytest.mark.skip_if_edition("saas")
def test_swagger_ui_http(site: Site) -> None:
    session = CMKWebSession(site)
    session.login()
    resp = session.get(f"/{site.id}/check_mk/api/v1/ui/index.html", expected_code=200)
    assert resp.headers["content-type"] == "text/html; charset=utf-8"
    assert '<script src="./swagger-initializer.js"' in resp.text
    resp = session.get(f"/{site.id}/check_mk/api/v1/ui/swagger-initializer.js", expected_code=200)
    assert "petstore" not in resp.text
    assert "openapi-swagger-ui.yaml" in resp.text


@pytest.mark.skip_if_edition("saas")
def test_swagger_ui_resource_urls(site: Site) -> None:
    session = CMKWebSession(site)
    session.login()
    resp = session.get(f"/{site.id}/check_mk/api/v1/ui/swagger-ui.js", expected_code=200)
    assert resp.headers["content-type"] in (
        "application/javascript; charset=utf-8",
        "text/javascript; charset=utf-8",
    )
    resp = session.get(f"/{site.id}/check_mk/api/v1/ui/swagger-ui.css", expected_code=200)
    assert resp.headers["content-type"] == "text/css; charset=utf-8"
    resp = session.get(f"/{site.id}/check_mk/api/v1/ui/swagger-ui.css.map", expected_code=200)
    assert resp.headers["content-type"] == "application/octet-stream"
