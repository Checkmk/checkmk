#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import json

import pytest
import yaml
from openapi_spec_validator import validate_spec

from tests.unit.cmk.gui.conftest import WebTestAppForCMK


def test_yaml_file_unauthenticated(wsgi_app: WebTestAppForCMK) -> None:
    wsgi_app.get("/NO_SITE/check_mk/api/1.0/openapi-swagger-ui.yaml", status=401)


def test_json_file_unauthenticated(wsgi_app: WebTestAppForCMK) -> None:
    wsgi_app.get("/NO_SITE/check_mk/api/1.0/openapi-doc.json", status=401)


# TODO(cr): This test takes ages, about 52s total! Improve this.
@pytest.mark.slow
def test_yaml_file_authenticated(logged_in_wsgi_app: WebTestAppForCMK) -> None:
    resp = logged_in_wsgi_app.get("/NO_SITE/check_mk/api/1.0/openapi-swagger-ui.yaml", status=200)
    assert resp.content_type.startswith("application/x-yaml")
    data = yaml.safe_load(resp.body)
    validate_spec(data)


# TODO(cr): This test takes ages, about 50s total! Improve this.
@pytest.mark.slow
def test_json_file_authenticated(logged_in_wsgi_app: WebTestAppForCMK) -> None:
    resp = logged_in_wsgi_app.get("/NO_SITE/check_mk/api/1.0/openapi-doc.json", status=200)
    assert resp.content_type.startswith("application/json")
    data = json.loads(resp.body)
    validate_spec(data)
