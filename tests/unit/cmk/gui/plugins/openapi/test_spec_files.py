#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

import pytest
import yaml
from openapi_spec_validator import validate_spec  # type: ignore[import]


# TODO(cr): This test takes ages, about 52s total! Improve this.
@pytest.mark.slow
def test_yaml_file(wsgi_app):
    resp = wsgi_app.get("/NO_SITE/check_mk/api/1.0/openapi-swagger-ui.yaml", status=200)
    assert resp.content_type.startswith("application/x-yaml")
    data = yaml.safe_load(resp.body)
    validate_spec(data)


# TODO(cr): This test takes ages, about 50s total! Improve this.
@pytest.mark.slow
def test_json_file(wsgi_app):
    resp = wsgi_app.get("/NO_SITE/check_mk/api/1.0/openapi-doc.json", status=200)
    assert resp.content_type.startswith("application/json")
    data = json.loads(resp.body)
    validate_spec(data)
