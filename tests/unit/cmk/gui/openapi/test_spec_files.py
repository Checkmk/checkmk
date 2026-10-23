#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from http import HTTPStatus
from pathlib import Path

import pytest
import yaml
from openapi_spec_validator import validate

from cmk.utils import paths
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK


@pytest.mark.usefixtures("request_context")
def test_yaml_file_unauthenticated(wsgi_app: WebTestAppForCMK) -> None:
    wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/openapi-swagger-ui.yaml", status=HTTPStatus.UNAUTHORIZED
    )


@pytest.mark.usefixtures("request_context")
def test_json_file_unauthenticated(wsgi_app: WebTestAppForCMK) -> None:
    wsgi_app.get("/NO_SITE/check_mk/api/1.0/openapi-doc.json", status=HTTPStatus.UNAUTHORIZED)


def _write_dummy_spec(spec_path: Path) -> None:
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        repr(
            {
                "info": {
                    "title": "Checkmk REST API",
                    "version": "1.0",
                },
                "openapi": "3.0.2",
                "paths": {},
            }
        )
    )


@pytest.mark.usefixtures("patch_theme")
def test_yaml_file_authenticated(logged_in_wsgi_app: WebTestAppForCMK) -> None:
    _write_dummy_spec(paths.doc_dir / "rest-api/spec/swagger-ui.spec")
    resp = logged_in_wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/openapi-swagger-ui.yaml", status=HTTPStatus.OK
    )
    assert resp.content_type.startswith("application/x-yaml")
    data = yaml.safe_load(resp.body)
    validate(data)


@pytest.mark.usefixtures("patch_theme")
def test_json_file_authenticated(logged_in_wsgi_app: WebTestAppForCMK) -> None:
    _write_dummy_spec(paths.doc_dir / "rest-api/spec/doc.spec")
    resp = logged_in_wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/openapi-doc.json", status=HTTPStatus.OK
    )
    assert resp.content_type.startswith("application/json")
    data = json.loads(resp.body)
    validate(data)
