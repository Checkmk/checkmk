#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

import pytest
import yaml
from openapi_spec_validator import validate

from tests.unit.cmk.web_test_app import WebTestAppForCMK

from cmk.utils import paths


def test_yaml_file_unauthenticated(wsgi_app: WebTestAppForCMK, request_context: None) -> None:
    wsgi_app.get("/NO_SITE/check_mk/api/1.0/openapi-swagger-ui.yaml", status=401)


def test_json_file_unauthenticated(wsgi_app: WebTestAppForCMK, request_context: None) -> None:
    wsgi_app.get("/NO_SITE/check_mk/api/1.0/openapi-doc.json", status=401)


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
    _write_dummy_spec(paths.var_dir / "rest_api/spec/swagger-ui.spec")
    resp = logged_in_wsgi_app.get("/NO_SITE/check_mk/api/1.0/openapi-swagger-ui.yaml", status=200)
    assert resp.content_type.startswith("application/x-yaml")
    data = yaml.safe_load(resp.body)
    validate(data)


@pytest.mark.usefixtures("patch_theme")
def test_json_file_authenticated(logged_in_wsgi_app: WebTestAppForCMK) -> None:
    _write_dummy_spec(paths.var_dir / "rest_api/spec/doc.spec")
    resp = logged_in_wsgi_app.get("/NO_SITE/check_mk/api/1.0/openapi-doc.json", status=200)
    assert resp.content_type.startswith("application/json")
    data = json.loads(resp.body)
    validate(data)
