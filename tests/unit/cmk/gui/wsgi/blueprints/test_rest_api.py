#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus
from urllib.parse import quote

import pytest

from cmk.utils import paths
from tests.unit.cmk.web_test_app import WebTestAppForCMK


@pytest.fixture(name="redoc_template")
def _redoc_template() -> None:
    template = paths.web_dir / "htdocs/openapi/index.html"
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_text("<redoc spec-url='{spec_url}'></redoc>")


@pytest.mark.usefixtures("redoc_template")
def test_versioned_doc_rejects_unknown_version(wsgi_app: WebTestAppForCMK) -> None:
    version = quote("'><img src=x onerror=alert(1)>")

    wsgi_app.get(f"/NO_SITE/check_mk/api/{version}/doc/", status=HTTPStatus.NOT_FOUND)


@pytest.mark.usefixtures("redoc_template")
@pytest.mark.parametrize(
    "version, spec_version",
    [("v1", "v1"), ("1.0", "v1"), ("unstable", "unstable")],
)
def test_versioned_doc_points_to_spec_of_requested_version(
    wsgi_app: WebTestAppForCMK, version: str, spec_version: str
) -> None:
    response = wsgi_app.get(f"/NO_SITE/check_mk/api/{version}/doc/", status=HTTPStatus.OK)

    assert f"spec-url='../../{spec_version}/openapi-doc.yaml'" in response.text
